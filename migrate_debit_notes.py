import pandas as pd
from datetime import datetime

def get_tax(name, amount, type_tax_use='purchase'):
    t = env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', type_tax_use)], limit=1)
    if not t:
        t = env['account.tax'].create({
            'name': name, 'amount': amount,
            'type_tax_use': type_tax_use, 'amount_type': 'percent'
        })
    return t.id

def get_partner(name):
    p = env['res.partner'].search([('name', '=', name)], limit=1)
    if not p:
        p = env['res.partner'].create({'name': name, 'supplier_rank': 1})
    return p.id

def migrate_debit_notes():
    fname = '/home/biz/odoo/new_debit_note_register.xlsx'
    print(f"Reading {fname} with pandas...")
    df = pd.read_excel(fname, header=None)
    
    # ── 1. DELETE existing debit notes (in_refund) ───────────────────
    print("Deleting existing supplier refunds (Debit Notes)...")
    existing = env['account.move'].search([('move_type', '=', 'in_refund')])
    if existing:
        for m in existing:
            if m.state != 'draft': m.button_draft()
        existing.unlink()
        env.cr.commit()
        print(f"  Deleted {len(existing)} records.")
    
    journal = env['account.journal'].search([('type', '=', 'purchase')], limit=1)
    count = 0
    errors = 0
    
    # Data starts from row 10 (index 9)
    for idx, row in df.iloc[9:].iterrows():
        r = row.tolist()
        if not any(pd.notna(x) for x in r): continue
        
        raw_date = r[0]
        part_name = str(r[1]).strip() if pd.notna(r[1]) else ''
        vref = str(r[3]).strip() if pd.notna(r[3]) else f"MIG/DN/{idx}"
        
        try: taxable_value = float(r[4] or 0)
        except: taxable_value = 0.0
            
        try: gross_total = float(r[5] or 0)
        except: gross_total = 0.0
            
        try: igst_amt = float(r[7] or 0)
        except: igst_amt = 0.0
            
        try: cgst_amt = float(r[10] or 0)
        except: cgst_amt = 0.0
            
        try: sgst_amt = float(r[11] or 0)
        except: sgst_amt = 0.0
        
        if not part_name or 'Total' in part_name or part_name == 'nan': continue
        
        if isinstance(raw_date, (datetime, pd.Timestamp)):
            dt_str = raw_date.strftime('%Y-%m-%d')
        else:
            try:
                dt_str = str(raw_date)[:10]
                if ' ' in dt_str: dt_str = dt_str.split(' ')[0]
            except:
                dt_str = datetime.now().strftime('%Y-%m-%d')
                
        # Determine tax IDs
        tax_ids = []
        if igst_amt > 0:
            tax_ids = [get_tax('IGST 18%', 18.0)]
        elif cgst_amt > 0 or sgst_amt > 0:
            tax_ids = [get_tax('CGST 9%', 9.0), get_tax('SGST 9%', 9.0)]
        else:
            if taxable_value > 0 and abs(gross_total - taxable_value * 1.18) < 1.0:
                 tax_ids = [get_tax('GST 18%', 18.0)]
        
        try:
            move = env['account.move'].create({
                'move_type': 'in_refund',
                'partner_id': get_partner(part_name),
                'invoice_date': dt_str,
                'date': dt_str,
                'ref': vref,
                'journal_id': journal.id,
                'invoice_line_ids': [(0, 0, {
                    'name': 'Debit Note (Migration)',
                    'quantity': 1,
                    'price_unit': round(taxable_value, 2),
                    'tax_ids': [(6, 0, tax_ids)],
                })],
            })
            move.action_post()
            count += 1
        except Exception as e:
            errors += 1
            print(f"  ERR row {idx}: {e}")
            
    env.cr.commit()
    print(f"\nMigration Finished. Total Debit Notes: {count} | Errors: {errors}")

migrate_debit_notes()
