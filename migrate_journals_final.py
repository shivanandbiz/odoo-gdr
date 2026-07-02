import pandas as pd
from datetime import datetime

def get_partner(name):
    if not name: return None
    return env['res.partner'].search([('name', '=ilike', name)], limit=1)

def get_account(name):
    if not name: return None
    name = name.split('(')[0].strip()
    a = env['account.account'].search([('name', 'ilike', name)], limit=1)
    if not a:
        a = env['account.account'].search([('account_type', '=', 'expense')], limit=1)
    return a

def migrate_journals():
    fname = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
    print(f"Reading Journal Register from {fname}...")
    df = pd.read_excel(fname, sheet_name='Journal Register', header=None)
    
    headers = df.iloc[8].tolist()
    accounts_map = {}
    for i in range(7, len(headers)):
        if pd.notna(headers[i]):
            accounts_map[i] = str(headers[i]).strip()
            
    print(f"Mapped {len(accounts_map)} columns.")

    print("Cleaning up older journal migration data (ref like JOUR_MIG/)...")
    env['account.move'].search([('ref', 'like', 'JOUR_MIG/%')]).button_draft()
    env['account.move'].search([('ref', 'like', 'JOUR_MIG/%')]).unlink()
    env.cr.commit()
    
    count = 0
    errors = 0
    
    # Iterate all rows, skipping noise
    for idx, row in df.iloc[9:].iterrows():
        r = row.tolist()
        
        # Identification of data rows
        raw_date = r[0]
        part_name = str(r[1]).strip() if pd.notna(r[1]) else ''
        
        # Skip Headers/Footers
        if not part_name or part_name in ['nan', 'Particulars', 'Grand Total', 'Total:']: continue
        if 'GDR MEKTEK' in part_name or 'Bangalore' in part_name or 'Ramanagara' in part_name: continue
        if not isinstance(raw_date, (datetime, pd.Timestamp)) and not (isinstance(raw_date, str) and len(raw_date) >= 10):
            continue

        vtype = str(r[2]).strip() if pd.notna(r[2]) else 'Journal'
        vref = str(r[3]).strip() if pd.notna(r[3]) and str(r[3]) != 'nan' else f"J_{idx}"
        
        line_vals = []
        total_debit = 0.0
        
        for col_idx, acc_name in accounts_map.items():
            if col_idx < len(r) and pd.notna(r[col_idx]):
                try:
                    val = float(r[col_idx])
                    if val != 0:
                        acc = get_account(acc_name)
                        line_vals.append({
                            'name': acc_name,
                            'account_id': acc.id,
                            'debit': val if val > 0 else 0.0,
                            'credit': -val if val < 0 else 0.0,
                        })
                        total_debit += val
                except: continue
        
        if total_debit == 0 and not line_vals: continue
        
        partner = get_partner(part_name)
        if partner:
            cr_acc_id = partner.property_account_payable_id.id
        else:
            acc = env['account.account'].search([('name', 'ilike', part_name)], limit=1)
            if acc:
                cr_acc_id = acc.id
            else:
                partner = env['res.partner'].create({'name': part_name, 'supplier_rank': 1})
                cr_acc_id = partner.property_account_payable_id.id
        
        line_vals.append({
            'name': f"Counterpart: {part_name}",
            'account_id': cr_acc_id,
            'partner_id': partner.id if partner else False,
            'debit': -total_debit if total_debit < 0 else 0.0,
            'credit': total_debit if total_debit > 0 else 0.0,
        })

        dt_str = raw_date.strftime('%Y-%m-%d') if isinstance(raw_date, datetime) else str(raw_date)[:10]

        try:
            journal = env['account.journal'].search([('type', '=', 'general')], limit=1)
            m_dr = sum(l['debit'] for l in line_vals)
            m_cr = sum(l['credit'] for l in line_vals)
            if abs(m_dr - m_cr) > 0.01:
                line_vals[-1]['credit'] += (m_dr - m_cr)

            move = env['account.move'].create({
                'move_type': 'entry',
                'date': dt_str,
                'ref': f"JOUR_MIG/{vref}",
                'journal_id': journal.id,
                'line_ids': [(0, 0, l) for l in line_vals]
            })
            move.action_post()
            count += 1
            if count % 200 == 0:
                print(f"  Migrated {count} journals...")
            
        except Exception as e:
            errors += 1
            
    env.cr.commit()
    print(f"\nJournal Migration Finished.")
    print(f"Total Migrated: {count} | Errors: {errors}")

migrate_journals()
