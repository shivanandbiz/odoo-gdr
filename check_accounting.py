import sys
from odoo import fields

def check_accounting():
    print("--- ACCOUNTING VERIFICATION ---")
    company = env.company
    print(f"Company: {company.name}")
    print(f"Fiscal Year Start: {company.compute_fiscalyear_dates(env.context.get('date') or fields.Date.today())['date_from']}")
    
    # Opening Balance
    opening_moves = env['account.move'].search([('date', '<=', company.compute_fiscalyear_dates(env.context.get('date') or fields.Date.today())['date_from'])])
    print(f"\n1. Opening Balances:")
    print(f"   Found {len(opening_moves)} moves before or on the start of fiscal year.")
    unposted_opening = opening_moves.filtered(lambda m: m.state != 'posted')
    if unposted_opening:
        print(f"   WARNING: There are {len(unposted_opening)} UNPOSTED opening moves!")
    else:
        print("   All opening moves are posted.")
        
    # Unposted Records
    draft_moves = env['account.move'].search([('state', '=', 'draft')])
    print(f"\n2. Unposted Records (Drafts):")
    print(f"   Total Draft Journal Entries: {len(draft_moves)}")
    for m_type in set(draft_moves.mapped('move_type')):
        count = len(draft_moves.filtered(lambda m: m.move_type == m_type))
        print(f"     - {m_type}: {count}")

    # Balance Sheet Summary
    accounts = env['account.account'].search([])
    assets = liabilities = equity = income = expense = 0.0
    
    for acc in accounts:
        env.cr.execute("SELECT sum(balance) FROM account_move_line WHERE account_id = %s AND parent_state = 'posted'", [acc.id])
        res = env.cr.fetchone()
        balance = res[0] or 0.0
        
        acc_type = acc.account_type
        if acc_type in ('asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current', 'asset_prepayments', 'asset_fixed'):
            assets += balance
        elif acc_type in ('liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current'):
            liabilities += balance
        elif acc_type in ('equity', 'equity_unallocated'):
            equity += balance
        elif acc_type in ('income', 'income_other'):
            income += balance
        elif acc_type in ('expense', 'expense_depreciation', 'expense_direct_cost'):
            expense += balance

    print(f"\n3. Balance Sheet Check:")
    print(f"   Total Assets:      {assets:,.2f}")
    print(f"   Total Liabilities: {liabilities * -1:,.2f}")
    print(f"   Total Equity:      {equity * -1:,.2f}")
    
    print(f"\n4. Profit & Loss Check:")
    print(f"   Total Income:  {income * -1:,.2f} (Credit is negative in DB)") 
    print(f"   Total Expense: {expense:,.2f} (Debit is positive in DB)")
    print(f"   Net Profit:    {(income * -1) - expense:,.2f}")

    print("\n5. Configuration:")
    print(f"   Tax Cash Basis: {company.tax_exigibility}")
    print(f"   Default Sale Tax: {company.account_sale_tax_id.name if company.account_sale_tax_id else 'None'}")
    print(f"   Default Purchase Tax: {company.account_purchase_tax_id.name if company.account_purchase_tax_id else 'None'}")
    print("--- END OF VERIFICATION ---")

try:
    check_accounting()
except Exception as e:
    print(f"Error: {e}")

