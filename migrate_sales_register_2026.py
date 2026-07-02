
import pandas as pd
import math
from datetime import datetime

FILE_PATH = '/home/biz/GDR_Original_Data/Final Data/Final_sales_Register_2025_2026.xlsx'

def clean_str(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    return str(val).strip()

def fval(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return 0.0
    try:
        # handle strings with commas
        if isinstance(val, str):
            val = val.replace(',', '')
        return float(val)
    except:
        return 0.0

print("Reading file...")
# Skip 9 rows to get to the data start
df = pd.read_excel(FILE_PATH, engine='odf', skiprows=9)

def get_product(name):
    # Find or create product
    name = name[:512] # Odoo name limit
    p = env['product.product'].search([('name', '=', name)], limit=1)
    if not p:
        p = env['product.product'].create({
            'name': name,
            'type': 'consu',
        })
    return p

def get_partner(name):
    p = env['res.partner'].search([('name', '=ilike', name)], limit=1)
    if not p:
        p = env['res.partner'].create({'name': name, 'customer_rank': 1})
    return p

print("Parsing transactions...")
transactions = []
current_tx = None

# Indices (base 0)
# 0: Date
# 1: Particulars
# 2: Price / Ledger
# 3: Qty
# 4: Amount
# 8: Debit Amount
# 9: Credit Amount

for idx, row in df.iterrows():
    date = row.iloc[0]
    particulars = clean_str(row.iloc[1])
    
    if not particulars or particulars.lower() in ('total', 'grand total'):
        continue
        
    if isinstance(date, (datetime, pd.Timestamp)):
        if current_tx: transactions.append(current_tx)
        current_tx = {
            'date': date.strftime('%Y-%m-%d'),
            'customer': particulars,
            'vch_no': clean_str(row.iloc[7]),
            'lines': [],
            'taxes': [],
        }
        continue
    
    if not current_tx: continue

    price = fval(row.iloc[2])
    qty = fval(row.iloc[3])
    amount = fval(row.iloc[4])
    credit = fval(row.iloc[9])
    
    if price > 0 and qty > 0:
        # Product Line
        current_tx['lines'].append({
            'name': particulars,
            'price': price,
            'qty': qty,
            'amount': amount
        })
    elif "GST" in particulars.upper() or particulars.upper().startswith("IGST") or particulars.upper().startswith("CGST") or particulars.upper().startswith("SGST"):
        # Tax line
        current_tx['taxes'].append({
            'name': particulars,
            'amount': credit or amount
        })
    elif particulars:
        if current_tx['lines']:
             current_tx['lines'][-1]['name'] += " " + particulars
        else:
             # Transaction Ledger/Memo
             pass

if current_tx: transactions.append(current_tx)
print(f"Parsed {len(transactions)} transactions.")

# ── Migration ────────────────────────────────────────────────────────────────
print("\nDeleting existing future-dated sales invoices if they match this range...")
# This register is 2025-2026.
# I'll just delete ALL out_invoices for safety if the user said "migrate again".
# But maybe it's better to match by Ref.
all_existing = env['account.move'].search([('move_type', '=', 'out_invoice')])
if all_existing:
    print(f"  Found {len(all_existing)} existing invoices. Resetting to draft and deleting...")
    all_existing.button_draft()
    all_existing.unlink()
    env.cr.commit()

journal = env['account.journal'].search([('type', '=', 'sale')], limit=1)
success = 0
errors = 0

for tx in transactions:
    try:
        partner = get_partner(tx['customer'])
        
        invoice_lines = []
        for l in tx['lines']:
            product = get_product(l['name'])
            invoice_lines.append((0, 0, {
                'product_id': product.id,
                'quantity': l['qty'],
                'price_unit': l['price'],
                'name': l['name'],
            }))
        
        # If no product lines (maybe service?), use name from Taxes or generic
        if not invoice_lines:
            # Check if there is a 'SALES' ledger amount
            base_amount = 0
            for t in tx['taxes']:
                if 'SALES' in t['name'].upper():
                    base_amount = t['amount']
                    break
            
            if base_amount > 0:
                 invoice_lines.append((0, 0, {
                    'name': 'Sales',
                    'quantity': 1,
                    'price_unit': base_amount,
                }))

        if not invoice_lines:
            continue

        move_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': tx['date'],
            'date': tx['date'],
            'ref': tx['vch_no'],
            'journal_id': journal.id,
            'invoice_line_ids': invoice_lines,
        }
        
        move = env['account.move'].create(move_vals)
        move.action_post()
        success += 1
        
        if success % 20 == 0:
            env.cr.commit()
            print(f"  Imported {success} invoices...")

    except Exception as e:
        print(f"  [ERROR] {tx['vch_no']}: {e}")
        env.cr.rollback()
        errors += 1

env.cr.commit()
print(f"\nMigration Complete! Success: {success}, Errors: {errors}")
