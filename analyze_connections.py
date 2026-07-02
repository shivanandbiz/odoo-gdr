
def analyze_connections(env):
    print("=== Odoo Data Connectivity Analysis ===")
    
    # 1. Customers and Invoices
    partners = env['res.partner'].search([])
    invoices = env['account.move'].search([('move_type', '=', 'out_invoice')])
    
    partners_with_invoices = invoices.mapped('partner_id')
    print(f"Total Partners: {len(partners)}")
    print(f"Partners with Invoices: {len(partners_with_invoices)}")
    
    # 2. Invoices and Reconciliation
    fully_paid_invoices = invoices.filtered(lambda r: r.payment_state in ('paid', 'in_payment'))
    partially_paid_invoices = invoices.filtered(lambda r: r.payment_state == 'partial')
    unpaid_invoices = invoices.filtered(lambda r: r.payment_state == 'not_paid')
    
    print(f"\nInvoice Payment States:")
    print(f" - Fully Paid/In Payment: {len(fully_paid_invoices)}")
    print(f" - Partially Paid: {len(partially_paid_invoices)}")
    print(f" - Unpaid: {len(unpaid_invoices)}")
    print(f"Total Invoices: {len(invoices)}")
    
    # 3. Payments and their Moves
    payments = env['account.payment'].search([('partner_type', '=', 'customer')])
    payments_with_move = payments.filtered(lambda r: r.move_id)
    payments_without_move = payments.filtered(lambda r: not r.move_id)
    
    print(f"\nCustomer Payments:")
    print(f" - Total Payments: {len(payments)}")
    print(f" - Payments with Accounting Move: {len(payments_with_move)}")
    print(f" - Payments without Accounting Move: {len(payments_without_move)}")
    
    # 4. Reconciliation Details (Partial reconciles)
    # How many payments are actually linked to invoices
    reconciled_moves = env['account.partial.reconcile'].search([])
    print(f"\nReconciliation Activity:")
    print(f" - Total Partial Reconciliations: {len(reconciled_moves)}")
    
    # 5. Check for orphans
    orphaned_invoices = invoices.filtered(lambda r: not r.partner_id)
    print(f"\nData Integrity:")
    print(f" - Invoices without Partner: {len(orphaned_invoices)}")
    
    # 6. Specific check for the 'Cancelled Record'
    cancelled_partner = env['res.partner'].search([('name', '=', 'Cancelled Record')], limit=1)
    if cancelled_partner:
        cancelled_invoices = invoices.filtered(lambda r: r.partner_id == cancelled_partner)
        print(f" - Invoices linked to 'Cancelled Record': {len(cancelled_invoices)}")

if __name__ == "__main__":
    analyze_connections(env)
