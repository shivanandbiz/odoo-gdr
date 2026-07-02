import odoo

def fix_payment_zero_amounts_sql_v2():
    print("=== Fixing Zero Amounts via Raw SQL (v2) ===")
    
    # Update amount_company_currency_signed
    
    env.cr.execute("SELECT id, amount, payment_type FROM account_payment WHERE state NOT IN ('draft', 'cancel')")
    payments = env.cr.fetchall()
    
    fixed = 0
    for pid, amount, ptype in payments:
        if not amount: continue
        
        sign = 1 if ptype == 'inbound' else -1
        signed_amt = amount * sign
        
        env.cr.execute("""
            UPDATE account_payment 
            SET amount_company_currency_signed = %s
            WHERE id = %s
        """, (signed_amt, pid))
        
        fixed += 1
        
    env.cr.commit()
    print(f"Successfully processed {fixed} payments via SQL.")

fix_payment_zero_amounts_sql_v2()
