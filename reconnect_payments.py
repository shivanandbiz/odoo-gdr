import odoo

def reconnect_payments():
    print("=== Reconnecting Payments to Invoices (Case-Insensitive) ===")
    
    # Get all unreconciled inbound payments
    payments = env['account.payment'].search([
        ('payment_type', '=', 'inbound'),
        ('state', '=', 'posted')
    ])
    
    already_done = 0
    reconnected = 0
    failed = 0
    
    for pay in payments:
        # Check if already reconciled via move lines
        pay_line = pay.move_id.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
        if not pay_line:
            already_done += 1
            continue
            
        partner_name = pay.partner_id.name
        
        # 1. Find all partners with similar names (case-insensitive)
        similar_partners = env['res.partner'].search([('name', '=ilike', partner_name)])
        
        # 2. Find open invoices for all these partner variations
        invoices = env['account.move'].search([
            ('partner_id', 'in', similar_partners.ids),
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('state', '=', 'posted')
        ], order='date asc')
        
        if invoices:
            inv_lines = invoices.mapped('line_ids').filtered(
                lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled and l.debit > 0
            )
            
            if inv_lines:
                try:
                    print(f"  ➜ Reconnecting {partner_name} (Pay: {pay.name}) with {len(invoices)} invoices...")
                    (pay_line | inv_lines).reconcile()
                    reconnected += 1
                except Exception as e:
                    print(f"    ✗ Failed: {e}")
                    failed += 1
                    
    env.cr.commit()
    print(f"\nReconnection Finished.")
    print(f"Already Reconciled: {already_done}")
    print(f"Newly Reconnected: {reconnected}")
    print(f"Failed: {failed}")

reconnect_payments()
