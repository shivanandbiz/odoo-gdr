
import pandas as pd
import math
import re
from datetime import datetime

FILE_PATH = '/home/biz/GDR_Original_Data/Final Data/Final_sales_Register_2025_2026.xlsx'

def clean_str(val):
    if pd.isna(val): return ""
    return str(val).strip()

def fval(val):
    if pd.isna(val): return 0.0
    try:
        if isinstance(val, str):
            val = val.replace(',', '')
        return float(val)
    except:
        return 0.0

print("Reading Sales Register...")
df = pd.read_excel(FILE_PATH, header=None)

# Skip headers
# Row 8 is 'Particulars'
all_data = df.iloc[9:]

invoices = []
current_inv = None

for idx, row in all_data.iterrows():
    date = row.iloc[0]
    inv_no = clean_str(row.iloc[2])
    party = clean_str(row.iloc[3])
    
    # Check if this starts a new invoice
    # A new invoice has a date OR a Voucher Number starting with GDR/
    if (isinstance(date, (datetime, pd.Timestamp)) or (isinstance(date, str) and len(date) > 5)) and inv_no.startswith('GDR/'):
        if current_inv:
            invoices.append(current_inv)
        
        current_inv = {
            'date': date if isinstance(date, (datetime, pd.Timestamp)) else pd.to_datetime(date),
            'ref': inv_no,
            'partner': party,
            'lines': [],
            'taxes': []
        }
        continue
    
    if not current_inv: continue
    
    # Parse lines within the invoice
    particulars = clean_str(row.iloc[3])
    
    # Try to identify line type
    # Col 6 often has the amount
    amount = fval(row.iloc[6])
    amount_alt = fval(row.iloc[9])
    
    if "CGST" in particulars.upper() or "SGST" in particulars.upper() or "IGST" in particulars.upper():
        current_inv['taxes'].append({'name': particulars, 'amount': amount_alt or amount})
    elif particulars and amount > 0:
        # Check if it's a product (Internal Ref format 9xx-xxxxx or just a description)
        if re.search(r'\d{3}-\d{5}', particulars) or amount > 100: # Heuristic
             current_inv['lines'].append({
                 'name': particulars,
                 'amount': amount,
                 'qty': 1.0 # Default if unknown
             })

if current_inv:
    invoices.append(current_inv)

print(f"Total Invoices found: {len(invoices)}")

# ── Migration ────────────────────────────────────────────────────────────────
journal = env['account.journal'].search([('type', '=', 'sale')], limit=1)
# Use the GST 18% tax we created
tax_18 = env['account.tax'].search([('name', '=', 'GST 18%'), ('type_tax_use', '=', 'sale')], limit=1)

success = 0
for inv in invoices:
    try:
        partner = env['res.partner'].search([('name', '=ilike', inv['partner'])], limit=1)
        if not partner:
            partner = env['res.partner'].create({'name': inv['partner']})
            
        invoice_lines = []
        for l in inv['lines']:
            # Search product by internal ref or name
            product = env['product.product'].search(['|', ('default_code', '=', l['name']), ('name', '=', l['name'])], limit=1)
            if not product:
                # Create a generic service if not found
                product = env['product.product'].create({
                    'name': l['name'],
                    'type': 'consu',
                    'default_code': l['name'] if len(l['name']) < 20 else False
                })
            
            invoice_lines.append((0, 0, {
                'product_id': product.id,
                'name': l['name'],
                'quantity': 1,
                'price_unit': l['amount'],
                'tax_ids': [(6, 0, [tax_18.id])] if tax_18 else []
            }))
            
        if not invoice_lines: continue
        
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
        
        if success % 50 == 0:
            env.cr.commit()
            print(f"Imported {success} invoices...")
            
    except Exception as e:
        print(f"Error importing {inv['ref']}: {e}")
        env.cr.rollback()

env.cr.commit()
print(f"Migration completed. Total imported: {success}")
