
import pandas as pd
from datetime import datetime
import odoo
from odoo import api, SUPERUSER_ID

def get_partner_intelligent(env, name):
    name = str(name).strip()
    if not name or name.lower() == 'nan': return False
    partner = env['res.partner'].search([('name', '=ilike', name)], limit=1)
    if not partner:
        clean_name = name.replace('PVT LTD', '').replace('PRIVATE LIMITED', '').replace('Ltd', '').replace('Pvt', '').strip()
        partner = env['res.partner'].search([('name', 'ilike', clean_name)], limit=1)
    return partner

_account_cache = {}

def get_or_create_account(env, name):
    name = str(name).strip()
    if not name or name.lower() == 'nan': return False
    
    if name in _account_cache:
        return _account_cache[name]
        
    acc = env['account.account'].search([('name', '=', name)], limit=1)
    if not acc:
        acc = env['account.account'].search([('name', '=ilike', name)], limit=1)
        
    if not acc:
        # Create it with a safe code
        last_acc = env['account.account'].search([('code', '=like', '99%')], order='code desc', limit=1)
        if last_acc:
            code_val = int(last_acc.code)
        else:
            code_val = 990000
            
        # Ensure we don't pick a code already in cache
        for cached_acc in _account_cache.values():
            try:
                c_val = int(cached_acc.code)
                if c_val >= code_val:
                    code_val = c_val
            except: pass
            
        new_code = str(code_val + 1)
            
        acc_type = 'expense'
        name_upper = name.upper()
        if 'GST' in name_upper or 'TAX' in name_upper:
            acc_type = 'asset_current'
        elif 'PAYABLE' in name_upper:
            acc_type = 'liability_payable'
        elif 'RECEIVABLE' in name_upper:
            acc_type = 'asset_receivable'
            
        acc = env['account.account'].create({
            'name': name,
            'code': new_code,
            'account_type': acc_type,
        })
        print(f"Created Account: {name} ({new_code})")
        
    _account_cache[name] = acc
    return acc

def migrate_journals(env):
    file_path = '/home/biz/GDR_Original_Data/Final Data/Journal_Register_2025_2026.xlsx'
    df = pd.read_excel(file_path, sheet_name='Sheet1', header=8)
    df = df[pd.to_datetime(df['Date'], errors='coerce').notna()]
    
    print(f"Total Journal records to process: {len(df)}")
    
    misc_journal = env['account.journal'].search([('code', '=', 'MISC')], limit=1)
    if not misc_journal:
        misc_journal = env['account.journal'].search([('type', '=', 'general')], limit=1)
    
    count = 0
    errors = 0
    # Columns from index 7 onwards are accounts
    account_cols = df.columns.tolist()[7:]

    for idx, row in df.iterrows():
        try:
            date_val = row['Date']
            dt_str = pd.to_datetime(date_val).strftime('%Y-%m-%d')
            particulars_name = str(row['Particulars']).strip()
            
            if not particulars_name or particulars_name.lower() == 'nan' or 'total' in particulars_name.lower():
                continue
                
            gross_total = float(row['Gross Total'] or 0)
            if gross_total == 0: continue
            
            ref = f"JV/25-26/{idx}"
            if env['account.move'].search_count([('ref', '=', ref)]):
                continue
            
            partner = get_partner_intelligent(env, particulars_name)
            particulars_account = None
            if partner:
                particulars_account = partner.property_account_payable_id
            else:
                particulars_account = get_or_create_account(env, particulars_name)
            
            if not particulars_account:
                continue

            line_ids = []
            sum_cols = 0.0
            
            for col in account_cols:
                val = row[col]
                if pd.notna(val) and float(val or 0) != 0:
                    amount = float(val)
                    acc = get_or_create_account(env, col)
                    if acc:
                        line_ids.append((0, 0, {
                            'name': f"Journal: {particulars_name}",
                            'account_id': acc.id,
                            'debit': amount if amount > 0 else 0,
                            'credit': abs(amount) if amount < 0 else 0,
                            'partner_id': partner.id if partner else False,
                        }))
                        sum_cols += amount
            
            # The balancing line from Particulars
            # If sum_cols is POSITIVE (Total Debit), then Particulars is CREDIT
            line_ids.append((0, 0, {
                'name': f"Journal: {particulars_name}",
                'account_id': particulars_account.id,
                'debit': abs(sum_cols) if sum_cols < 0 else 0,
                'credit': sum_cols if sum_cols > 0 else 0,
                'partner_id': partner.id if partner else False,
            }))
            
            # Verify balance
            total_debit = sum(l[2]['debit'] for l in line_ids)
            total_credit = sum(l[2]['credit'] for l in line_ids)
            
            if abs(total_debit - total_credit) > 0.01:
                # Add rounding line
                line_ids.append((0, 0, {
                    'name': "Rounding",
                    'account_id': env['account.account'].search([('name', 'ilike', 'Rounding')], limit=1).id or particulars_account.id,
                    'debit': total_credit - total_debit if total_credit > total_debit else 0,
                    'credit': total_debit - total_credit if total_debit > total_credit else 0,
                }))

            move = env['account.move'].create({
                'move_type': 'entry',
                'date': dt_str,
                'ref': ref,
                'journal_id': misc_journal.id,
                'line_ids': line_ids
            })
            move.action_post()
            count += 1
            if count % 100 == 0:
                env.cr.commit()
                print(f"Migrated {count} entries...")
                
        except Exception as e:
            print(f"Error at idx {idx}: {e}")
            errors += 1
            env.cr.rollback()

    env.cr.commit()
    print(f"\nFINISH: Migrated {count} journal entries. Errors: {errors}")

if __name__ == "__main__":
    migrate_journals(env)
