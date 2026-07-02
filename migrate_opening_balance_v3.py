
import pandas as pd
import math
import re

def migrate_opening_balance():
    print("=== Opening Balance Migration (As of 1 Apr 2025) ===")
    
    file_path = '/home/biz/GDR_Original_Data/Final Data/Opening Balance apr 2025.xlsx'
    # header=None to handle the complex Tally header manually
    df = pd.read_excel(file_path, header=None)
    
    # Data starts at index 12 (row 13)
    # Ends at index 911 (before Grand Total at 912)
    data = df.iloc[12:912].copy()
    data.columns = ['Name', 'Dr_Opening', 'Cr_Opening', 'Debit', 'Credit']
    
    # We use the 'Debit' and 'Credit' columns (indices 3 and 4) as they represent the finalized balance
    data['Debit'] = pd.to_numeric(data['Debit'], errors='coerce').fillna(0)
    data['Credit'] = pd.to_numeric(data['Credit'], errors='coerce').fillna(0)
    data = data.dropna(subset=['Name'])
    
    print(f"Total rows to process: {len(data)}")

    # Account mapping logic
    def get_account_type(name, dr, cr):
        name_upper = str(name).upper()
        
        # Heuristics based on name
        if any(kw in name_upper for kw in ['BANK', 'C/A', 'A/C', 'ACCOUNT', 'SBI', 'KOTAK', 'INDIAN BANK', 'HDFC', 'CANARA', 'SVC']):
            return 'asset_cash'
        
        if any(kw in name_upper for kw in ['GST', 'IGST', 'CGST', 'SGST', 'TDS', 'VAT', 'TAX', 'DUTIES']):
            if dr > 0: return 'asset_current'
            else: return 'liability_current'
            
        if any(kw in name_upper for kw in ['FIXED ASSETS', 'PLANT', 'MACHINERY', 'BUILDING', 'COMPUTER', 'FURNITURE', 'VEHICLE']):
            return 'asset_non_current'
            
        if 'CAPITAL' in name_upper:
            return 'equity'
            
        if 'OPENING STOCK' in name_upper:
            return 'asset_current' # Inventory

        # Default to Receivable/Payable if it looks like a person/company
        # If it has a balance and is not clearly an asset/liability
        if dr > 0: return 'asset_receivable'
        return 'liability_payable'

    line_ids = []
    
    # System accounts
    receivable_acc = env['account.account'].search([('account_type', '=', 'asset_receivable')], limit=1)
    payable_acc = env['account.account'].search([('account_type', '=', 'liability_payable')], limit=1)
    
    for _, row in data.iterrows():
        name = str(row['Name']).strip()
        dr = row['Debit']
        cr = row['Credit']
        
        if dr == 0 and cr == 0: continue
        
        # Skip items that might be sub-items of stock? 
        # In Tally Trial Balance, sometimes items are listed. 
        # But our sum-check showed they are ALL needed to balance.
        
        acc_type = get_account_type(name, dr, cr)
        
        partner_id = False
        account_id = False
        
        if acc_type in ['asset_receivable', 'liability_payable']:
            # Search for partner
            partner = env['res.partner'].search([('name', '=', name)], limit=1)
            if not partner:
                # If not found, check if we should create it or if it's a false positive
                # For now, create it to ensure balance
                partner = env['res.partner'].create({'name': name})
            partner_id = partner.id
            account_id = receivable_acc.id if dr > 0 else payable_acc.id
        else:
            # For other ledgers, find by name or create
            acc = env['account.account'].search([('name', '=', name)], limit=1)
            if not acc:
                print(f"Creating account: {name} ({acc_type})")
                # Generate a code
                last_acc = env['account.account'].search([], order='code desc', limit=1)
                try:
                    new_code = str(int(last_acc.code) + 1)
                except:
                    new_code = "OB" + str(idx)
                    
                acc = env['account.account'].create({
                    'code': new_code,
                    'name': name,
                    'account_type': acc_type,
                })
            account_id = acc.id

        line_ids.append((0, 0, {
            'account_id': account_id,
            'partner_id': partner_id,
            'name': f"Opening Balance: {name}",
            'debit': dr,
            'credit': cr,
        }))

    # Create the Journal Entry
    journal = env['account.journal'].search([('code', 'in', ['MISC', 'GEN', 'OPEN'])], limit=1)
    
    move = env['account.move'].create({
        'move_type': 'entry',
        'date': '2025-04-01',
        'ref': 'OPENING/2025-04-01',
        'journal_id': journal.id,
        'line_ids': line_ids
    })
    
    total_db = sum(l[2]['debit'] for l in line_ids)
    total_cr = sum(l[2]['credit'] for l in line_ids)
    print(f"Entry Created: {move.name or 'Draft'} | Dr: {total_db} | Cr: {total_cr}")
    
    if abs(total_db - total_cr) < 0.01:
        move.action_post()
        env.cr.commit()
        print("Success: Opening balances posted.")
    else:
        print(f"Warning: Transaction out of balance by {abs(total_db - total_cr)}. Kept as Draft.")
        env.cr.commit()

if __name__ == "__main__":
    migrate_opening_balance()
