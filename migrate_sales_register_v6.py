
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
df = pd.read_excel(FILE_PATH, header=None)

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

for idx in range(len(df)):
    row = df.iloc[idx]
    date_val = row.iloc[0]
    vch_no = clean_str(row.iloc[2])
    particulars = clean_str(row.iloc[3])
    
    is_date = isinstance(date_val, (datetime, pd.Timestamp))
    
    # Header Row Check
    if is_date and vch_no:
        if current_inv:
            invoices.append(current_inv)
        
        current_inv = {
            'date': date_val,
            'ref': vch_no,
            'partner': particulars,
            'lines': [],
            'tax_names': set(),
            'total_amt': fval(row.iloc[6])
        }
        continue
    
    if not current_inv:
        continue
        
    p_up = particulars.upper()
    qty = fval(row.iloc[4])
    amount_base = fval(row.iloc[6])
    tax_amt = fval(row.iloc[9])
    
    # Is it a Tax Line?
    is_tax = False
    for t_key in TAX_MAP:
        if t_key.replace(" ","") in p_up.replace(" ",""):
            current_inv['tax_names'].add(TAX_MAP[t_key])
            is_tax = True
            break
    if is_tax: continue
    
    # Ignore rows that are not useful
    if not particulars or "SALES" in p_up or "NEW REF" in p_up or "TOTAL" in p_up:
        continue
        
    # Is it a Product Line or Description?
    if qty > 0 or amount_base > 0:
        current_inv['lines'].append({
            'name': particulars,
            'qty': qty if qty > 0 else 1.0,
            'price': amount_base,
        })
    elif current_inv['lines']:
        # Concatenate description to the last item
        current_inv['lines'][-1]['name'] += " " + particulars

if current_inv:
    invoices.append(current_inv)

print(f"Total Invoices parsed: {len(invoices)}")
if invoices:
    print(f"Sample: {invoices[0]['ref']} | {invoices[0]['partner']} | Lines: {len(invoices[0]['lines'])}")

# ── Odoo Migration ───────────────────────────────────────────────────────────
from odoo import api

success = 0
journal = env['account.journal'].search([('type', '=', 'sale')], limit=1)

for inv in invoices:
    try:
        # 1. Partner
        partner = env['res.partner'].search([('name', '=ilike', inv['partner'])], limit=1)
        if not partner:
            partner = env['res.partner'].create({'name': inv['partner']})
            
        # 2. Taxes
        tax_ids = []
        for tn in inv['tax_names']:
            tax = env['account.tax'].search([('name', '=', tn), ('type_tax_use', '=', 'sale')], limit=1)
            if tax: tax_ids.append(tax.id)
            
        # 3. Lines
        invoice_lines = []
        for l in inv['lines']:
            # Determine Product
            code_match = re.search(r'\d{3}-\d{5}', l['name'])
            search_code = code_match.group(0) if code_match else None
            
            product = None
            if search_code:
                product = env['product.product'].search([('default_code', '=', search_code)], limit=1)
            if not product:
                product = env['product.product'].search([('name', '=', l['name'][:512])], limit=1)
            
            if not product:
                product = env['product.product'].create({
                    'name': l['name'][:512],
                    'type': 'consu',
                    'default_code': search_code or False
                })
            
            invoice_lines.append((0, 0, {
                'product_id': product.id,
                'name': l['name'],
                'quantity': l['qty'],
                'price_unit': l['price'] / l['qty'] if l['qty'] > 0 else l['price'],
                'tax_ids': [(6, 0, tax_ids)]
            }))
            
        if not invoice_lines: continue
        
        # 4. Invoice
        move = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': inv['date'],
            'ref': inv['ref'],
            'journal_id': journal.id,
            'invoice_line_ids': invoice_lines,
        })
        # Try to post
        try:
            move.action_post()
            success += 1
        except Exception as post_err:
            print(f"  [Draft Only] {inv['ref']}: {post_err}")
            success += 1 # Still counted as imported
            
        if success % 20 == 0:
            env.cr.commit()
            print(f"  Imported {success}...")

    except Exception as e:
        print(f"Error {inv['ref']}: {e}")
        env.cr.rollback()

env.cr.commit()
print(f"Final Count: {success}")
