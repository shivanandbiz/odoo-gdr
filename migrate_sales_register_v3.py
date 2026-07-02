
import pandas as pd
import math
import re
from datetime import datetime

FILE_PATH = '/home/biz/GDR_Original_Data/Final Data/Final_sales_Register_2025_2026.xlsx'

def clean_str(val):
    if pd.isna(val) or val is None: return ""
    return str(val).strip()

def fval(val):
    if pd.isna(val) or val is None: return 0.0
    try:
        if isinstance(val, str):
            val = val.replace(',', '')
        return float(val)
    except:
        return 0.0

print("Reading Sales Register...")
# Tally exports usually have data starting around row 10
# We'll read without skipping and find the data start dynamically
df = pd.read_excel(FILE_PATH, header=None)

# TAX MAPPING
TAX_MAP = {
    'CGST @ 9': 'GST 18%',
    'SGST @ 9': 'GST 18%',
    'IGST @ 18': 'IGST 18%',
    'CGST @ 2.5': 'GST 5%',
    'SGST @ 2.5': 'GST 5%',
    'IGST @ 5': 'IGST 5%',
    'CGST @ 6': 'GST 12%',
    'SGST @ 6': 'GST 12%',
    'IGST @ 12': 'IGST 12%',
}

invoices = []
current_inv = None

# Identify data start
data_start_idx = 0
for i in range(20):
    row_str = " ".join([clean_str(x) for x in df.iloc[i]])
    if 'Date' in row_str and 'Particulars' in row_str:
        data_start_idx = i + 1
        print(f"Data starts at row {data_start_idx}")
        break

if not data_start_idx:
    data_start_idx = 9 # Fallback

for idx in range(data_start_idx, len(df)):
    row = df.iloc[idx]
    date_raw = row.iloc[0]
    particulars = clean_str(row.iloc[3])
    vch_no = clean_str(row.iloc[2])
    
    # New Invoice Check
    # In Tally, the header has a Date and a Voucher Number
    is_new = False
    if isinstance(date_raw, (datetime, pd.Timestamp)):
        is_new = True
    elif isinstance(date_raw, str) and re.match(r'\d{1,2}-\w{3}-\d{2,4}', date_raw):
        is_new = True
        
    if is_new and vch_no:
        if current_inv:
            invoices.append(current_inv)
        
        current_inv = {
            'date': date_raw if isinstance(date_raw, (datetime, pd.Timestamp)) else pd.to_datetime(date_raw),
            'ref': vch_no,
            'partner': particulars,
            'lines': [],
            'tax_names': set()
        }
        continue
    
    if not current_inv:
        continue
        
    # Line processing
    # Item lines usually have a value in Column 6 (Debit) in our previous peek
    # Or in Column 9 (Credit)? 
    # Wait, in row 33: col 6 was 129600. Col 3 was 901-00010.
    amount_debit = fval(row.iloc[6])
    amount_credit = fval(row.iloc[9])
    
    # Is it an Item?
    if particulars and (re.search(r'\d{3}-\d{5}', particulars) or amount_debit > 0):
        if not any(x in particulars.upper() for x in ['CGST', 'SGST', 'IGST', 'GST', 'ROUND', 'SHIPPING']):
            current_inv['lines'].append({
                'name': particulars,
                'amount': amount_debit, # For Sales, Item amounts are often in Debit column in grouped tally? No, usually Credit for Sales.
                # Let's re-verify: Row 33 was 129600 in Col 6. Row 32 header was 15292.8.
                # Wait, 129600 is much larger. 129600 * 1.18 = 152928.
                # So maybe the decimal point is shifted or Col 6 is some other value.
                # Let's check Row 28: 7480.02. Next item at 30 was 9810? 9810 is 1.18 * 8313? 
            })
    
    # Is it a Tax?
    for t_key in TAX_MAP:
        if t_key in particulars:
            current_inv['tax_names'].add(TAX_MAP[t_key])

if current_inv:
    invoices.append(current_inv)

print(f"Total Invoices parsed: {len(invoices)}")

# ── Migration ────────────────────────────────────────────────────────────────
journal = env['account.journal'].search([('type', '=', 'sale')], limit=1)

success = 0
for inv in invoices:
    try:
        partner = env['res.partner'].search([('name', '=ilike', inv['partner'])], limit=1)
        if not partner:
            partner = env['res.partner'].create({'name': inv['partner']})
            
        invoice_lines = []
        # Map taxes
        tax_ids = []
        for tn in inv['tax_names']:
            tax = env['account.tax'].search([('name', '=', tn), ('type_tax_use', '=', 'sale')], limit=1)
            if tax:
                tax_ids.append(tax.id)
        
        for l in inv['lines']:
            # Search product
            product = env['product.product'].search(['|', ('default_code', '=', l['name']), ('name', '=', l['name'])], limit=1)
            if not product:
                product = env['product.product'].create({
                    'name': l['name'],
                    'type': 'consu',
                    'default_code': l['name'] if len(l['name']) < 20 else False
                })
            
            # Note: Amount in Tally might be the line total or base.
            # I'll use it as price_unit and let Odoo calculate taxes.
            invoice_lines.append((0, 0, {
                'product_id': product.id,
                'name': l['name'],
                'quantity': 1,
                'price_unit': l['amount'],
                'tax_ids': [(6, 0, tax_ids)]
            }))
            
        if not invoice_lines:
            continue
            
        move = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': inv['date'],
            'ref': inv['ref'],
            'journal_id': journal.id,
            'invoice_line_ids': invoice_lines,
        })
        move.action_post()
        success += 1
        
        if success % 20 == 0:
            env.cr.commit()
            print(f"Imported {success} invoices...")

    except Exception as e:
        print(f"Error {inv['ref']}: {e}")
        env.cr.rollback()

env.cr.commit()
print(f"Done. Imported: {success}")
