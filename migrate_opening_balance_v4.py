
import pandas as pd
import math
import re

def migrate_opening_balance():
    print("=== Opening Balance Migration (As of 1 Apr 2025) ===")
    
    file_path = '/home/biz/GDR_Original_Data/Final Data/Opening Balance apr 2025.xlsx'
    df = pd.read_excel(file_path, header=None)
    
    # Data starts after headers, approximately index 12 (row 13)
    data = df.iloc[12:912].copy()
    data.columns = ['Name', 'Dr_Opening', 'Cr_Opening', 'Debit', 'Credit']
    
    data['Debit'] = pd.to_numeric(data['Debit'], errors='coerce').fillna(0)
    data['Credit'] = pd.to_numeric(data['Credit'], errors='coerce').fillna(0)
    data = data.dropna(subset=['Name'])
    
    # 1. Pre-fetch existing info
    existing_accounts = {a.name: a for a in env['account.account'].search([])}
    # Get highest numeric code and start from there + 1
    codes = [int(c) for c in env['account.account'].search([]).mapped('code') if c.isdigit()]
    next_code = (max(codes) + 1) if codes else 100001
    
    # Ensure next_code is not one of the "special" ones like 1000000 if it was causing issues
    if next_code >= 1000000:
        # Check if there are gaps or use a different range
        next_code = 110000 
        # Verify 110000 is not taken
        taken_codes = set(env['account.account'].search([]).mapped('code'))
        while str(next_code) in taken_codes:
            next_code += 1

    print(f"Starting new account codes from: {next_code}")

    def get_account_type(name, dr, cr):
        name_upper = str(name).upper()
        if any(kw in name_upper for kw in ['BANK', 'C/A', 'A/C', 'ACCOUNT', 'SBI', 'KOTAK', 'INDIAN BANK', 'HDFC', 'CANARA', 'SVC']):
            return 'asset_cash'
        if any(kw in name_upper for kw in ['GST', 'IGST', 'CGST', 'SGST', 'TDS', 'VAT', 'TAX', 'DUTIES']):
            return 'asset_current' if dr > 0 else 'liability_current'
        if any(kw in name_upper for kw in ['FIXED ASSETS', 'PLANT', 'MACHINERY', 'BUILDING', 'COMPUTER', 'FURNITURE', 'VEHICLE']):
            return 'asset_non_current'
        if 'CAPITAL' in name_upper:
            return 'equity'
        if 'OPENING STOCK' in name_upper:
            return 'asset_current'
        return 'asset_receivable' if dr > 0 else 'liability_payable'

    line_ids = []
    
    receivable_acc = env['account.account'].search([('account_type', '=', 'asset_receivable')], limit=1)
    payable_acc = env['account.account'].search([('account_type', '=', 'liability_payable')], limit=1)
    
    code_counter = next_code
    
    for idx, row in data.iterrows():
        name = str(row['Name']).strip()
        dr = row['Debit']
        cr = row['Credit']
        
        if dr == 0 and cr == 0: continue
        
        acc_type = get_account_type(name, dr, cr)
        
        partner_id = False
        account_id = False
        
        if acc_type in ['asset_receivable', 'liability_payable']:
            partner = env['res.partner'].search([('name', '=', name)], limit=1)
            if not partner:
                partner = env['res.partner'].create({'name': name})
            partner_id = partner.id
            account_id = receivable_acc.id if dr > 0 else payable_acc.id
        else:
            if name in existing_accounts:
                account_id = existing_accounts[name].id
            else:
                # Create account with unique code
                print(f"Creating account: {name} (Code: {code_counter})")
                acc = env['account.account'].create({
                    'code': str(code_counter),
                    'name': name,
                    'account_type': acc_type,
                })
                account_id = acc.id
                existing_accounts[name] = acc
                code_counter += 1

        line_ids.append((0, 0, {
            'account_id': account_id,
            'partner_id': partner_id,
            'name': f"Opening Balance: {name}",
            'debit': dr,
            'credit': cr,
        }))

    journal = env['account.journal'].search([('code', 'in', ['MISC', 'GEN', 'OPEN'])], limit=1)
    if not journal:
        journal = env['account.journal'].search([('type', '=', 'general')], limit=1)

    move = env['account.move'].create({
        'move_type': 'entry',
        'date': '2025-04-01',
        'ref': 'OPENING/2025-04-01',
        'journal_id': journal.id,
        'line_ids': line_ids
    })
    
    total_db = sum(l[2]['debit'] for l in line_ids)
    total_cr = sum(l[2]['credit'] for l in line_ids)
    print(f"Entry Created: {move.ref} | Dr: {total_db:,.2f} | Cr: {total_cr:,.2f}")
    
    if abs(total_db - total_cr) < 0.01:
        move.action_post()
        env.cr.commit()
        print("Success: Opening balances posted.")
    else:
        print(f"Warning: Transaction out of balance by {abs(total_db - total_cr):,.2f}. Kept as Draft.")
        env.cr.commit()

if __name__ == "__main__":
    migrate_opening_balance()
