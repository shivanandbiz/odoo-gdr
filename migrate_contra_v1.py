
import pandas as pd
from datetime import datetime

def get_account(env, name):
    name = str(name).strip()
    if not name or name.lower() == 'nan': return False
    acc = env['account.account'].search([('name', 'ilike', name)], limit=1)
    if not acc:
        # Try finding journal and its default account
        j = env['account.journal'].search([('name', 'ilike', name)], limit=1)
        if j: acc = j.default_account_id
    return acc

def migrate_contra(env):
    file_path = '/home/biz/GDR_Original_Data/Final Data/Contra_Register_2025_2026.xlsx'
    # The header is at row 7 (index 7), so header=8 in pandas skips 8 rows and uses the 9th as header labels?
    # Wait, earlier I used header=8 and it worked. 
    df = pd.read_excel(file_path, sheet_name='Sheet1', header=8)
    
    misc_journal = env['account.journal'].search([('code', '=', 'MISC')], limit=1)
    if not misc_journal:
        misc_journal = env['account.journal'].search([('type', '=', 'general')], limit=1)
        
    count = 0
    
    bank_cols = ['HDFC C/A 50200024612749', 'PETTY CASH ACCOUNT', 'Kotak -3545975369', 'Indian Bank - 7554757298']

    for idx, row in df.iterrows():
        try:
            date_val = row['Date']
            if not pd.notna(date_val) or str(date_val).strip() == '': 
                continue
            
            try:
                dt_str = pd.to_datetime(date_val).strftime('%Y-%m-%d')
            except: 
                continue
                
            target_name = str(row['Particulars']).strip()
            if not target_name or target_name.lower() == 'nan' or 'total' in target_name.lower():
                continue
                
            try:
                amount = float(row['Gross Total'])
            except:
                amount = 0.0
                
            if amount <= 0: continue
            
            source_account = None
            for col in bank_cols:
                if col in row and pd.notna(row[col]) and float(row[col] or 0) != 0:
                    source_account = get_account(env, col)
                    # We also update the amount in case it's more accurate in the column
                    amount = abs(float(row[col]))
                    break
            
            target_account = get_account(env, target_name)
            
            if not source_account or not target_account:
                print(f"Skipping row {idx}: Account not found. Source: {source_account.name if source_account else 'None'}, Target: {target_name}")
                continue
            
            ref = f"CONTRA/25-26/{idx}"
            
            if env['account.move'].search_count([('ref', '=', ref)]):
                print(f"Row {idx} already migrated. Skipping.")
                continue

            move = env['account.move'].create({
                'move_type': 'entry',
                'date': dt_str,
                'ref': ref,
                'journal_id': misc_journal.id,
                'line_ids': [
                    (0, 0, {
                        'name': f"Contra: {target_account.name}",
                        'account_id': target_account.id,
                        'debit': amount,
                    }),
                    (0, 0, {
                        'name': f"Contra: {target_account.name}",
                        'account_id': source_account.id,
                        'credit': amount,
                    }),
                ]
            })
            move.action_post()
            count += 1
            print(f"Migrated row {idx}: {source_account.name} -> {target_account.name} ({amount})")
            
        except Exception as e:
            print(f"Error at idx {idx}: {e}")

    env.cr.commit()
    print(f"FINISH: Migrated {count} contra entries.")

if __name__ == "__main__":
    migrate_contra(env)
