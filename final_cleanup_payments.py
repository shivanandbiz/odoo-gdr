import odoo

def final_cleanup_payments():
    print("=== Final Cleanup of Payments (Sign and Status) ===")
    
    # 1. Fix Status to 'paid' for all posted payments
    payments = env['account.payment'].search([
        ('state', 'in', ['in_process', 'posted']),
        ('is_reconciled', '=', False)
    ])
    print(f"  Attempting to set {len(payments)} payments to 'paid' state...")
    for p in payments:
        try:
            p.state = 'paid'
        except Exception as e:
            print(f"    Could not set {p.name} to paid: {e}")
            
    # 2. Fix Signs (Customer Payments should be Inbound)
    # If a payment is in the Customer Payments section but is 'outbound', it shows a minus.
    # We should ensure they are 'inbound' and the move lines match (Bank Debit).
    customer_payments = env['account.payment'].search([
        ('partner_type', '=', 'customer'),
        ('payment_type', '=', 'outbound')
    ])
    
    print(f"  Fixing sign for {len(customer_payments)} customer payments...")
    for p in customer_payments:
        print(f"    Flipping {p.name} back to Inbound (Positive Sign)")
        # To flip back safely:
        # Move to draft, change type, flip lines, post
        move = p.move_id
        if move:
            p.action_draft()
            # Swap Dr/Cr on ALL lines
            for line in move.line_ids:
                dr, cr = line.debit, line.credit
                line.with_context(check_move_validity=False).write({
                    'debit': cr,
                    'credit': dr,
                    'amount_currency': -line.amount_currency if line.currency_id else 0
                })
            p.payment_type = 'inbound'
            p.action_post()
            p.state = 'paid'
            
    # 3. Same for Vendor Payments (should be outbound and positive)
    # Actually Odoo shows Outbound Vendor Payments as positive in the Vendor menu.
    # If they show with a minus, maybe they are 'inbound'.
    vendor_payments = env['account.payment'].search([
        ('partner_type', '=', 'supplier'),
        ('payment_type', '=', 'inbound')
    ])
    print(f"  Fixing sign for {len(vendor_payments)} vendor payments...")
    for p in vendor_payments:
        print(f"    Flipping {p.name} to Outbound (Positive Sign in Vendor menu)")
        move = p.move_id
        if move:
            p.action_draft()
            for line in move.line_ids:
                dr, cr = line.debit, line.credit
                line.with_context(check_move_validity=False).write({
                    'debit': cr,
                    'credit': dr,
                    'amount_currency': -line.amount_currency if line.currency_id else 0
                })
            p.payment_type = 'outbound'
            p.action_post()
            p.state = 'paid'

    env.cr.commit()
    print("Done.")

if __name__ == "__main__":
    final_cleanup_payments()
