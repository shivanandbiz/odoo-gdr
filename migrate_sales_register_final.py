
import pandas as pd
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

# Headers (Detected from previous run)
col_date = 0
col_part = 1
col_vch = 7
col_debit = 8
col_credit = 9

# Lines
line_part = 1
line_qty = 2
line_rate = 3
line_amt = 4

invoices = []
current_inv = None

TAX_MAP = {
    'CGST': 'GST 18%', 'SGST': 'GST 18%', 'IGST': 'IGST 18%',
    'CGST @ 9': 'GST 18%', 'SGST @ 9': 'GST 18%', 'IGST @ 18': 'IGST 18%',
}

for idx in range(9, len(df)):
    row = df.iloc[idx]
    date_val = row.iloc[col_date]
    vch_no = clean_str(row.iloc[col_vch])
    particulars = clean_str(row.iloc[col_part])
    
    # Relaxed new invoice check: Just look for Voucher Number starting with GDR
    if vch_no.startswith('GDR'):
        if current_inv: invoices.append(current_inv)
        
        # Determine Date
        if isinstance(date_val, (datetime, pd.Timestamp)):
            d = date_val
        else:
            d = pd.to_datetime(date_val, errors='coerce')
            if pd.isna(d):
                # Look at previous row or next row? Use fallback or propagate
                d = invoices[-1]['date'] if invoices else datetime(2025, 4, 1)

        current_inv = {
            'date': d, 'ref': vch_no, 'partner': particulars,
            'lines': [], 'tax_names': set(), 'is_cancelled': 'CANCELLED' in particulars.upper()
        }
        continue
    
    if not current_inv: continue
    
    p_up = particulars.upper()
    qty = fval(row.iloc[line_qty])
    rate = fval(row.iloc[line_rate])
    amt = fval(row.iloc[line_amt])
    
    # 1. Check for Tax
    is_tax_row = False
    for t_key in ['CGST', 'SGST', 'IGST']:
        if t_key in p_up:
            if '18' in p_up or '9' in p_up: current_inv['tax_names'].add('GST 18%' if 'IGST' not in p_up else 'IGST 18%')
            elif '5' in p_up or '2.5' in p_up: current_inv['tax_names'].add('GST 5%' if 'IGST' not in p_up else 'IGST 5%')
            is_tax_row = True
            break
    if is_tax_row: continue
    
    if "SALES" in p_up or "NEW REF" in p_up or "TOTAL" in p_up:
        continue
        
    # 2. Line
    if qty > 0 or amt > 0:
        current_inv['lines'].append({
            'name': particulars, 'qty': qty if qty > 0 else 1.0, 'price': rate if rate > 0 else amt,
        })
    elif particulars and current_inv['lines']:
        if not any(x in p_up for x in ['REFERENCE', 'VOUCHER']):
            current_inv['lines'][-1]['name'] += " " + particulars

if current_inv:
    invoices.append(current_inv)

print(f"Total Parsed: {len(invoices)}")

# ── Odoo Logic ───────────────────────────────────────────────────────────────
success = 0
journal = env['account.journal'].search([('type', '=', 'sale')], limit=1)

for inv in invoices:
    try:
        # Check existing
        existing = env['account.move'].search([('ref', '=', inv['ref']), ('move_type', '=', 'out_invoice')], limit=1)
        if existing: continue
        
        # 1. Partner
        p_name = inv['partner'] if not inv['is_cancelled'] else "Cancelled Customer"
        partner = env['res.partner'].search([('name', '=ilike', p_name)], limit=1) or env['res.partner'].create({'name': p_name})
            
        move_lines = []
        if inv['is_cancelled']:
            # For cancelled, we need at least one line to post
            product = env['product.product'].search([('name', '=', 'Cancelled')], limit=1) or env['product.product'].create({'name': 'Cancelled', 'type': 'service'})
            move_lines.append((0, 0, {
                'product_id': product.id, 'name': 'Cancelled Invoice', 'quantity': 1, 'price_unit': 0.0
            }))
        else:
            tax_ids = []
            for tn in inv['tax_names']:
                tax = env['account.tax'].search([('name', '=', tn), ('type_tax_use', '=', 'sale')], limit=1)
                if tax: tax_ids.append(tax.id)
                
            for l in inv['lines']:
                product = env['product.product'].search([('name', '=', l['name'][:512])], limit=1) or \
                          env['product.product'].search([('default_code', '=', l['name'][:512])], limit=1)
                if not product:
                    match = re.search(r'\d{3}-\d{5}', l['name'])
                    if match: product = env['product.product'].search([('default_code', '=', match.group(0))], limit=1)
                
                if not product:
                    product = env['product.product'].create({'name': l['name'][:512], 'type': 'consu'})
                
                move_lines.append((0, 0, {
                    'product_id': product.id, 'name': l['name'], 'quantity': l['qty'], 'price_unit': l['price'],
                    'tax_ids': [(6, 0, tax_ids)]
                }))
            
        if not move_lines: 
            # If still no lines, add a placeholder
            product = env['product.product'].search([], limit=1)
            move_lines.append((0, 0, {'product_id': product.id, 'name': 'Missing Lines', 'quantity': 1, 'price_unit': 0}))

        move = env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': partner.id, 'invoice_date': inv['date'],
            'ref': inv['ref'], 'journal_id': journal.id, 'invoice_line_ids': move_lines,
        })
        
        if inv['is_cancelled']:
            move.button_cancel()
        else:
            try:
                move.action_post()
            except:
                pass
            
        success += 1
        if success % 20 == 0:
            env.cr.commit()
            print(f"  Imported {success}...")
    except Exception as e:
        print(f"Error {inv['ref']}: {e}")
        env.cr.rollback()

env.cr.commit()
print(f"Finished. Total New Imported: {success}")
EOF
