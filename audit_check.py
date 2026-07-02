import odoo

def analyze_audit_readiness():
    print("=" * 60)
    print("   FY 2025-2026 AUDIT READINESS REPORT   ")
    print("=" * 60)
    
    start_date = '2025-04-01'
    end_date = '2026-03-31'
    
    # 1. Trial Balance (Debits vs Credits)
    env.cr.execute("""
        SELECT SUM(debit), SUM(credit) 
        FROM account_move_line 
        WHERE date >= %s AND date <= %s AND parent_state = 'posted'
    """, (start_date, end_date))
    res = env.cr.fetchone()
    total_debit = res[0] or 0.0
    total_credit = res[1] or 0.0
    
    print("\n--- 1. TRIAL BALANCE ---")
    print(f"Total Debits : ₹ {total_debit:>15,.2f}")
    print(f"Total Credits: ₹ {total_credit:>15,.2f}")
    if abs(total_debit - total_credit) < 0.01:
        print("-> [PASS] Debits perfectly equal Credits.")
    else:
        print(f"-> [FAIL] Imbalance: ₹ {abs(total_debit - total_credit):,.2f}")

    # 2. Financial Overview (P&L and Balance Sheet classes)
    # In modern Odoo (15+), account_type classifies accounts: 
    #   asset_*, liability_*, equity_*, income, expense
    env.cr.execute("""
        SELECT 
            CASE 
                WHEN a.account_type LIKE 'asset%%' THEN 'Assets'
                WHEN a.account_type LIKE 'liability%%' THEN 'Liabilities'
                WHEN a.account_type LIKE 'equity%%' THEN 'Equity'
                WHEN a.account_type LIKE 'income%%' THEN 'Income'
                WHEN a.account_type LIKE 'expense%%' THEN 'Expenses'
                ELSE 'Other'
            END as category,
            SUM(l.balance)
        FROM account_move_line l
        JOIN account_account a ON l.account_id = a.id
        WHERE l.date >= %s AND l.date <= %s AND l.parent_state = 'posted'
        GROUP BY 1
    """, (start_date, end_date))
    
    fin_res = env.cr.fetchall()
    fin_map = {r[0]: r[1] for r in fin_res}
    
    income = fin_map.get('Income', 0.0) * -1 # Credit is positive income
    expenses = fin_map.get('Expenses', 0.0) # Debit is positive expense
    net_profit = income - expenses
    
    assets = fin_map.get('Assets', 0.0) # Debit
    liabilities = fin_map.get('Liabilities', 0.0) * -1 # Credit
    equity = fin_map.get('Equity', 0.0) * -1 # Credit
    
    bs_diff = assets - (liabilities + equity + net_profit)
    
    print("\n--- 2. PROFIT AND LOSS ---")
    print(f"Total Income : ₹ {income:>15,.2f}")
    print(f"Total Expense: ₹ {expenses:>15,.2f}")
    print("-" * 35)
    print(f"Net Profit   : ₹ {net_profit:>15,.2f}")
    
    print("\n--- 3. BALANCE SHEET ---")
    print(f"Assets       : ₹ {assets:>15,.2f}")
    print(f"Liabilities  : ₹ {liabilities:>15,.2f}")
    print(f"Equity       : ₹ {equity:>15,.2f}")
    print(f"Curr. Profit : ₹ {net_profit:>15,.2f}")
    print("-" * 35)
    print(f"B.S. Variance: ₹ {bs_diff:>15,.2f}")
    
    if abs(bs_diff) < 0.01:
        print("-> [PASS] Accounting Equation balances (Assets = Liab + Equity + Profit)")
    else:
        print("-> [FAIL] Accounting Equation imbalance!")

    # 3. Suspense Account Check
    env.cr.execute("""
        SELECT a.name, SUM(l.balance)
        FROM account_move_line l
        JOIN account_account a ON l.account_id = a.id
        WHERE l.date >= %s AND l.date <= %s AND l.parent_state = 'posted'
        AND a.name ilike '%%suspense%%'
        GROUP BY a.name
    """, (start_date, end_date))
    suspense_res = env.cr.fetchall()
    
    print("\n--- 4. SUSPENSE / CLEARING ACCOUNTS ---")
    suspense_total = sum(abs(r[1]) for r in suspense_res)
    if not suspense_res or suspense_total < 0.01:
        print("-> [PASS] No hanging balances in suspense accounts.")
    else:
        print("-> [WARNING] Uncleared Suspense Balances Found!")
        for name, bal in suspense_res:
            print(f"   {name}: ₹ {bal:,.2f}")
            
    # 4. Opening Balance Check
    env.cr.execute("""
        SELECT SUM(balance) FROM account_move_line l
        JOIN account_journal j ON l.journal_id = j.id
        WHERE j.code = 'MISC' AND l.name ilike '%%opening%%'
    """)
    ob_bal = env.cr.fetchone()[0] or 0.0
    print("\n--- 5. OPENING BALANCES ---")
    if abs(ob_bal) < 0.01:
         print("-> [PASS] Opening Balances are fully netted to 0.")
    else:
         print(f"-> [WARNING] Imbalance in Opening Entries: ₹ {ob_bal:,.2f}")
         
    # 5. Reconciliation coverage
    env.cr.execute("""
        SELECT 
            COUNT(*) as total_payable_lines,
            SUM(CASE WHEN reconciled = TRUE THEN 1 ELSE 0 END) as rec_payable
        FROM account_move_line l
        JOIN account_account a ON l.account_id = a.id
        WHERE a.account_type = 'liability_payable' AND l.parent_state = 'posted'
          AND l.date >= %s AND l.date <= %s
    """, (start_date, end_date))
    pay_res = env.cr.fetchone()
    pay_cov = (pay_res[1] / pay_res[0] * 100) if pay_res[0] else 100.0
    
    env.cr.execute("""
        SELECT 
            COUNT(*) as total_receivable_lines,
            SUM(CASE WHEN reconciled = TRUE THEN 1 ELSE 0 END) as rec_recv
        FROM account_move_line l
        JOIN account_account a ON l.account_id = a.id
        WHERE a.account_type = 'asset_receivable' AND l.parent_state = 'posted'
          AND l.date >= %s AND l.date <= %s
    """, (start_date, end_date))
    recv_res = env.cr.fetchone()
    recv_cov = (recv_res[1] / recv_res[0] * 100) if recv_res[0] else 100.0
    
    print("\n--- 6. DATA HEALTH & RECONCILIATION ---")
    print(f"Payables Reconciliation Rate : {pay_cov:.1f}%")
    print(f"Receivables Reconciliation Rate: {recv_cov:.1f}%")

    print("\n" + "=" * 60)
    print("AUDIT PRE-CHECK COMPLETED")
    print("=" * 60)

analyze_audit_readiness()
