
def fix_payments(env):
    # Find payments with missing names or zero signed amount
    payments = env['account.payment'].search([('amount_company_currency_signed', '=', 0), ('amount', '>', 0)])
    print(f"Found {len(payments)} payments with zero signed amount.")
    
    for p in payments:
        if p.move_id:
            # Sync name if missing
            if not p.name:
                p.name = p.move_id.name
            
            # Trigger recompute of signs and amounts
            # We can try to just set the state again or call the compute method if available
            try:
                # In Odoo 16, this is often a computed field. 
                # We can try to force it by calling the compute method
                p._compute_amount_company_currency_signed()
            except Exception as e:
                # Fallback: manual calculation if method not accessible
                # For inbound payments, signed amount is positive
                p.amount_company_currency_signed = p.amount
            
            print(f"Fixed Payment {p.id}: Name {p.name}, Amount {p.amount}, Signed {p.amount_company_currency_signed}")
        else:
            print(f"Payment {p.id} has no move_id!")

    env.cr.commit()
    print("Fix complete.")

if __name__ == "__main__":
    # To be run in odoo shell
    fix_payments(env)
