# validate_balances_v1.py
import pandas as pd
import numpy as np

def validate():
    # Load Balance Sheet from Excel
    # Row 11 starts the liabilities/assets
    df = pd.read_excel('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', sheet_name='Balance Sheet', skiprows=10)
    
    # Excel structure: [Liabilities Name, Amount, Assets Name, Amount]
    # (Actually it's more like Col 0: Liab Name, Col 2: Liab Amt, Col 3: Asset Name, Col 5: Asset Amt)
    
    tally_balances = {}
    for i, row in df.iterrows():
        liab_name = str(row.iloc[0]).strip()
        liab_amt = row.iloc[2]
        asset_name = str(row.iloc[3]).strip()
        asset_amt = row.iloc[5]
        
        if liab_name != 'nan' and pd.notna(liab_amt):
            tally_balances[liab_name] = -float(liab_amt) # Neg for Liab
        if asset_name != 'nan' and pd.notna(asset_amt):
            tally_balances[asset_name] = float(asset_amt)

    print("--- TALLY BALANCES ---")
    # for k,v in tally_balances.items(): print(f"{k}: {v}")

    print("\n--- ODOO COMPARISON ---")
    # Matching logic: Since we created accounts with EXACT names, we search by name.
    mismatch = []
    for name, tally_val in tally_balances.items():
        if name in ['Total', 'Opening Balance', 'Current Period', 'Difference in opening balances']: continue
        
        account = env['account.account'].search([('name', '=', name)], limit=1)
        if not account:
            mismatch.append((name, tally_val, 'NOT FOUND'))
            continue
            
        # Get Odoo Balance
        # balance = debit - credit
        env.cr.execute("SELECT sum(debit - credit) FROM account_move_line WHERE account_id = %s", (account.id,))
        odoo_val = env.cr.fetchone()[0] or 0.0
        
        diff = abs(tally_val - odoo_val)
        if diff > 1.0: # allow small rounding
            mismatch.append((name, tally_val, odoo_val))
            
    if not mismatch:
        print("PERFECT MATCH! 100% Accuracy.")
    else:
        print(f"FOund {len(mismatch)} mismatches.")
        for m in mismatch:
            print(f"  {m[0]}: Tally={m[1]}, Odoo={m[2]}")

validate()
