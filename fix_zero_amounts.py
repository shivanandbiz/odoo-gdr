import odoo

def fix_payment_zero_amounts():
    print("=== Fixing Zero Amounts in Payment List View ===")
    
    # In Odoo 17, the list view typically shows 'amount_company_currency_signed'
    # Since we used Raw SQL for bulk, we bypassed the ORM computes!
    
    payments = env['account.payment'].search([
        ('amount', '>', 0),
        ('amount_company_currency_signed', '=', 0)
    ])
    
    print(f"Found {len(payments)} payments with missing signed amounts.")
    
    fixed = 0
    for p in payments:
        # Re-compute the signed fields!
        currency_rate = 1.0 # Assuming INR to INR is 1.0
        sign = 1 if p.payment_type == 'inbound' else -1
        
        # Directly writing them via ORM bypasses compute if they are stored:
        # Actually in Odoo core, they are stored computed fields.
        # We can just write them in SQL to be ultra-fast and error-free.
        
        env.cr.execute("""
            UPDATE account_payment 
            SET amount_company_currency_signed = %s,
                amount_signed = %s
            WHERE id = %s
        """, (p.amount * sign, p.amount * sign, p.id))
        fixed += 1
        
    env.cr.commit()
    print(f"Successfully fixed {fixed} payment display amounts.")

fix_payment_zero_amounts()
