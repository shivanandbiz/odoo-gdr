# migrate_sales_v2.py
import pandas as pd
import numpy as np

def migrate_sales():
    print("Reading Excel file...")
    df = pd.read_excel('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', 
                       sheet_name='Sales Inv. Register (2)', skiprows=8)
    
    # --- PHASE 1: PARSING ---
    print("Parsing sales data...")
    invoices = []
    current_inv = None
    
    for i, row in df.iterrows():
        date = row.iloc[0]
        particulars = str(row.iloc[1]).strip()
        qty = row.iloc[2]
        rate = row.iloc[3]
        line_val = row.iloc[4]
        vch_type = row.iloc[6]
        vch_no = row.iloc[7]
        debit = row.iloc[8]
        credit = row.iloc[9]
        
        if pd.notna(date) and pd.notna(vch_no) and particulars != 'nan':
            if 'Total' in particulars or 'cancelled' in particulars.lower(): continue
            dt_str = date.strftime('%Y-%m-%d')
            current_inv = {
                'date': dt_str,
                'customer': particulars,
                'ref': str(vch_no),
                'lines': [],
                'taxes_found': []
            }
            invoices.append(current_inv)
            continue
            
        if current_inv is None: continue
        
        # Item Line
        try:
            if pd.notna(qty) and pd.notna(rate) and particulars not in ['New Ref', 'nan']:
                current_inv['lines'].append({
                    'product': particulars,
                    'qty': float(qty),
                    'rate': float(rate),
                    'desc': ''
                })
                continue
        except:
            pass
            
        # Tax/Ledger Line
        if pd.notna(credit) and particulars != 'nan' and 'New Ref' not in particulars:
            current_inv['taxes_found'].append({'name': particulars, 'amount': float(credit)})
        elif pd.isna(qty) and pd.isna(rate) and pd.isna(line_val) and pd.isna(vch_no) and particulars != 'nan' and particulars != 'New Ref':
            if current_inv['lines']:
                current_inv['lines'][-1]['desc'] += ' ' + particulars

    print(f"Parsed {len(invoices)} valid invoices.")

    # --- PHASE 2: ODOO MIGRATION ---
    print("Clearing existing sales invoices...")
    old_moves = env['account.move'].search([('move_type', '=', 'out_invoice')])
    if old_moves:
        old_moves.button_draft()
        old_moves.unlink()
        env.cr.commit()

    journal = env['account.journal'].search([('type', '=', 'sale')], limit=1)
    
    # We found Odoo only has '18%' tax. We will map IGST 18 or CGST+SGST 18 to it.
    tax_18 = env['account.tax'].search([('name', '=', '18%'), ('type_tax_use', '=', 'sale')], limit=1)
    
    count = 0
    for inv in invoices:
        partner = env['res.partner'].search([('name', '=', inv['customer'])], limit=1)
        if not partner:
            partner = env['res.partner'].create({'name': inv['customer']})
            
        invoice_lines = []
        
        # Determine Taxes for the whole invoice
        tax_ids = []
        has_18 = any('18' in t['name'] or '9%' in t['name'] for t in inv['taxes_found'])
        if has_18 and tax_18:
            tax_ids = [tax_18.id]

        for line in inv['lines']:
            product = env['product.product'].search([('name', '=', line['product'])], limit=1)
            if not product:
                product = env['product.product'].create({
                    'name': line['product'],
                    'type': 'consu'
                })
            
            desc = (line['product'] + ' ' + line['desc']).strip()
            invoice_lines.append((0, 0, {
                'product_id': product.id,
                'quantity': line['qty'],
                'price_unit': line['rate'],
                'name': desc[:256],
                'tax_ids': [(6, 0, tax_ids)]
            }))

        if not invoice_lines: continue
        
        try:
            move = env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'invoice_date': inv['date'],
                'date': inv['date'],
                'ref': inv['ref'],
                'journal_id': journal.id,
                'invoice_line_ids': invoice_lines,
            })
            move.action_post()
            count += 1
            if count % 20 == 0:
                env.cr.commit()
                print(f"  ✓ Processed {count} invoices...")
        except Exception as e:
            print(f"Error on invoice {inv['ref']}: {e}")

    env.cr.commit()
    print(f"Successfully migrated {count} sales invoices.")

migrate_sales()
