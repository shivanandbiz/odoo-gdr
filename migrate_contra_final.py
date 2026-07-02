import pandas as pd
from datetime import datetime

def get_account(name):
    if not name: return None
    return env['account.account'].search([('name', 'ilike', name)], limit=1)

def get_journal(name):
    j = env['account.journal'].search([('name', 'ilike', name)], limit=1)
    if not j:
        j = env['account.journal'].search([('type', '=', 'bank')], limit=1)
    return j

def migrate_contra():
    fname = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
    print(f"Reading Contra from {fname}...")
    df = pd.read_excel(fname, sheet_name='Contra Register', header=None)
    
    # Headers are at Row 9 (Index 8)
    headers = df.iloc[8].tolist()
    accounts_map = {}
    for i in range(4, len(headers)):
        if pd.notna(headers[i]):
            accounts_map[i] = str(headers[i]).strip()
            
    print(f"Mapped {len(accounts_map)} source columns for Contra.")

    print("Cleaning up older contra migration data (ref like CONTR_MIG/)...")
    env['account.move'].search([('ref', 'like', 'CONTR_MIG/%')]).button_draft()
    env['account.move'].search([('ref', 'like', 'CONTR_MIG/%')]).unlink()
    env.cr.commit()
    
    count = 0
    errors = 0
    
    # Data starts from row 10 (Index 9) to row 42 (Index 41)
    for idx, row in df.iloc[9:42].iterrows():
        r = row.tolist()
        if not any(pd.notna(x) for x in r): continue
        if str(r[1]).strip() == 'Grand Total': break
        
        raw_date = r[0]
        part_name = str(r[1]).strip() if pd.notna(r[1]) else ''
        vref = f"C_{idx}"
        
        # Find amount and column account (In Contra, one side is PartName, other is in column)
        col_acc_name = None
        amount = 0.0
        for col_idx, acc_name in accounts_map.items():
            if col_idx < len(r) and pd.notna(r[col_idx]) and float(r[col_idx] or 0) != 0:
                col_acc_name = acc_name
                amount = abs(float(r[col_idx]))
                break
        
        if not col_acc_name or amount == 0: continue
        
        dt_str = datetime.now().strftime('%Y-%m-%d')
        if isinstance(raw_date, (datetime, pd.Timestamp)):
            dt_str = raw_date.strftime('%Y-%m-%d')
        elif pd.notna(raw_date):
            dt_str = str(raw_date)[:10]

        # In Contra sheet:
        # If I see "HDFC" in column 4 and "Kotak" in PartName (Row 9)
        # It means Kotak (DR) and HDFC (CR) if the amount is in HDFC column.
        # Wait, Tally Contra: CREDIT is usually the account in the column if it's a "Payment style" view.
        # Let's check Row 9: PartName = Kotak, Col HDFC has 95000. 
        # Usually means Transfer FROM HDFC TO Kotak.
        
        dr_name = part_name
        cr_name = col_acc_name

        try:
            dr_acc = get_account(dr_name)
            cr_acc = get_account(cr_name)
            
            # Select Journal (Prefer CR bank)
            journal = get_journal(cr_name)
            
            dr_acc_id = dr_acc.id if dr_acc else False
            cr_acc_id = cr_acc.id if cr_acc else journal.default_account_id.id
            
            if not dr_acc_id or not cr_acc_id:
                print(f"  ERR row {idx}: Account missing for {dr_name if not dr_acc_id else cr_name}")
                errors += 1
                continue

            move = env['account.move'].create({
                'move_type': 'entry',
                'date': dt_str,
                'ref': f"CONTR_MIG/{vref}",
                'journal_id': journal.id,
                'line_ids': [
                    (0, 0, {
                        'name': f"Contra: {dr_name} to {cr_name}",
                        'account_id': dr_acc_id,
                        'debit': amount,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': f"Contra: {dr_name} to {cr_name}",
                        'account_id': cr_acc_id,
                        'debit': 0.0,
                        'credit': amount,
                    }),
                ]
            })
            move.action_post()
            count += 1
            
        except Exception as e:
            errors += 1
            print(f"  ERR row {idx}: {e}")
            
    env.cr.commit()
    print(f"\nContra Migration Finished.")
    print(f"Total Migrated: {count} | Errors: {errors}")

migrate_contra()
