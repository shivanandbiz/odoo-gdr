import pandas as pd
import odoo

def migrate_opening_balance_ledger_wise():
    print("=== Ledger-wise Opening Balance Migration (Ref: new_gdr_Opening Balance apr 2025.xlsx) ===")
    
    file_path = '/home/biz/odoo/new_gdr_Opening Balance apr 2025.xlsx'
    df = pd.read_excel(file_path, sheet_name='Trial Balance', header=None)
    
    # 1. Prepare Data
    # Data starts after headers, approximately row 12 (index 11)
    # Ends before Grand Total (index 912)
    data = df.iloc[11:912].copy()
    data.columns = ['Name', 'c1', 'c2', 'Debit', 'Credit']
    data['Debit'] = pd.to_numeric(data['Debit'], errors='coerce').fillna(0)
    data['Credit'] = pd.to_numeric(data['Credit'], errors='coerce').fillna(0)
    data = data.dropna(subset=['Name'])

    # 2. Account Mapping Heuristics
    # We need:
    # - A generic Receivable account
    # - A generic Payable account
    # - Specific accounts for Banks, Fixed Assets, Taxes, Capital, Stock
    
    def get_account(name, balance_type):
        # balance_type: 'dr' or 'cr'
        name_upper = name.upper()
        
        # 1. FIXED ASSETS
        fa_keywords = ['PLANT', 'MACHINERY', 'BUILDING', 'COMPUTER', 'FURNITURE', 'OFFICE EQUIPMENT', 'VEHICLE', 'LAND']
        if any(kw in name_upper for kw in fa_keywords):
            return 'asset_non_current', 'Fixed Assets'
            
        # 2. BANKS / CASH
        bank_keywords = ['BANK', 'CASH', 'C/A', 'A/C', 'ACCOUNT', 'S/B', 'CURRENT A/C', 'CURRENR A/C']
        if any(kw in name_upper for kw in bank_keywords):
            return 'asset_current', 'Bank and Cash'
            
        # 3. TAXES
        tax_keywords = ['GST', 'IGST', 'CGST', 'SGST', 'TDS', 'VAT', 'TAX', 'DUTIES']
        if any(kw in name_upper for kw in tax_keywords):
            if balance_type == 'dr': return 'asset_current', 'Current Assets (Tax)'
            else: return 'liability_current', 'Current Liabilities (Tax)'
            
        # 4. CAPITAL
        if 'CAPITAL' in name_upper:
            return 'equity', 'Equity'
            
        # 5. STOCK
        if 'OPENING STOCK' in name_upper:
            return 'asset_current', 'Current Assets (Stock)'
            
        # 6. DIFFERENCE
        if 'DIFFERENCE' in name_upper:
            return 'equity', 'Opening Difference'
            
        # 7. PARTNERS (Default)
        if balance_type == 'dr':
            return 'asset_receivable', 'Receivable'
        else:
            return 'liability_payable', 'Payable'

    # 3. Create Entry Lines
    line_ids = []
    
    # We'll use these specific accounts if found, or create placeholders
    acc_cache = {}

    def get_odoo_account(acc_type, type_label):
        key = (acc_type, type_label)
        if key in acc_cache: return acc_cache[key]
        
        # Search for existing account of this type
        acc = env['account.account'].search([('account_type', '=', acc_type)], limit=1)
        if not acc:
            # Create a generic one if missing
            print(f"  Warning: No account of type {acc_type} found. Searching by name...")
            acc = env['account.account'].search([('name', 'ilike', type_label)], limit=1)
        
        if not acc:
            raise Exception(f"Could not find or create a valid Odoo account for {acc_type} ({type_label})")
            
        acc_cache[key] = acc.id
        return acc.id

    print(f"  Processing {len(data)} ledgers...")
    
    for _, row in data.iterrows():
        name = str(row['Name']).strip()
        dr = row['Debit']
        cr = row['Credit']
        
        if dr == 0 and cr == 0: continue
        
        bal_type = 'dr' if dr > 0 else 'cr'
        odoo_type, label = get_account(name, bal_type)
        
        partner_id = False
        # If it's a partner account, find or create partner
        if odoo_type in ['asset_receivable', 'liability_payable']:
            partner = env['res.partner'].search([('name', '=', name)], limit=1)
            if not partner:
                partner = env['res.partner'].create({'name': name})
            partner_id = partner.id
            
            # Map all partners to the standard Receivable/Payable accounts
            account_id = get_odoo_account(odoo_type, label)
        else:
            # For specific ledgers (Bank, FA, etc.), either find by name or create a sub-account
            # To keep it clean, we'll try to find an account with the EXACT name
            acc = env['account.account'].search([('name', '=', name)], limit=1)
            if not acc:
                # Create a specific account for these important ledgers
                # We'll use a prefix or specific code if possible
                code_prefix = 'OB'
                # Find a unique code
                existing_ob_codes = env['account.account'].search([('code', 'like', 'OB%')]).mapped('code')
                numeric_codes = [int(c[2:]) for c in existing_ob_codes if c[2:].isdigit()]
                next_num = max(numeric_codes) + 1 if numeric_codes else 1
                new_code = f"OB{next_num:04d}"
                
                print(f"  Creating ledger: {name} ({new_code})")
                acc = env['account.account'].create({
                    'code': new_code,
                    'name': name,
                    'account_type': odoo_type
                })
            account_id = acc.id

        line_ids.append((0, 0, {
            'account_id': account_id,
            'partner_id': partner_id,
            'name': f"Opening: {name}",
            'debit': dr,
            'credit': cr,
        }))

    # 4. Create and Post Move
    journal = env['account.journal'].search([('code', 'in', ['MISC', 'GEN', 'OPEN'])], limit=1)
    if not journal:
        journal = env['account.journal'].search([('type', '=', 'general')], limit=1)
        
    move = env['account.move'].create({
        'move_type': 'entry',
        'date': '2025-04-01',
        'ref': 'OPENING/2025-26/LEDGER-WISE',
        'journal_id': journal.id,
        'line_ids': line_ids
    })
    
    print(f"  ➜ Move created: {move.ref} with {len(line_ids)} lines")
    
    total_db = sum(l[2]['debit'] for l in line_ids)
    total_cr = sum(l[2]['credit'] for l in line_ids)
    print(f"  Final Totals -> Dr: {total_db:,.2f} | Cr: {total_cr:,.2f}")
    
    if abs(total_db - total_cr) < 0.01:
        move.action_post()
        env.cr.commit()
        print(f"  ➜ Entry POSTED successfully.")
    else:
        print(f"  ERROR: Entry is out of balance by {abs(total_db - total_cr):,.2f}. Saving as draft.")
        env.cr.commit()

if __name__ == "__main__":
    migrate_opening_balance_ledger_wise()
