import odoo

def fix_payment_zero_amounts_sql():
    print("=== Fixing Zero Amounts via Raw SQL ===")
    
    # In Odoo 17, the amount column might be amount_company_currency_signed
    # Let's forcefully update all payments that exist
    
    env.cr.execute("SELECT id, amount, payment_type FROM account_payment WHERE state NOT IN ('draft', 'cancel')")
    payments = env.cr.fetchall()
    
    fixed = 0
    for pid, amount, ptype in payments:
        if not amount: continue
        
        sign = 1 if ptype == 'inbound' else -1
        signed_amt = amount * sign
        
        env.cr.execute("""
            UPDATE account_payment 
            SET amount_company_currency_signed = %s,
                amount_signed = %s
            WHERE id = %s
        """, (signed_amt, signed_amt, pid))
        
        fixed += 1
        
    env.cr.commit()
    print(f"Successfully processed {fixed} payments via SQL.")

fix_payment_zero_amounts_sql()
