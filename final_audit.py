
def audit_accounting_connections(env):
    print("=== Comprehensive Accounting Audit ===")
    
    # 1. Invoice Audit
    invoices = env['account.move'].search([('move_type', '=', 'out_invoice')])
    total_inv = len(invoices)
    draft_inv = invoices.filtered(lambda r: r.state == 'draft')
    posted_inv = invoices.filtered(lambda r: r.state == 'posted')
    
    print(f"\n1. Invoices (Total: {total_inv})")
    print(f"   - Posted: {len(posted_inv)}")
    print(f"   - Draft: {len(draft_inv)}")
    
    # Check if lines exist and are balanced
    inv_without_lines = invoices.filtered(lambda r: not r.line_ids)
    print(f"   - Invoices without Lines: {len(inv_without_lines)}")

    # 2. Payment Audit
    payments = env['account.payment'].search([('partner_type', '=', 'customer')])
    total_pay = len(payments)
    linked_pay = payments.filtered(lambda r: r.move_id)
    unlinked_pay = payments.filtered(lambda r: not r.move_id)
    
    print(f"\n2. Customer Payments (Total: {total_pay})")
    print(f"   - Linked to Accounting (move_id): {len(linked_pay)}")
    print(f"   - Orphaned (no move_id): {len(unlinked_pay)}")
    
    # 3. Reconciliation Bridge Audit
    fully_paid = invoices.filtered(lambda r: r.payment_state == 'paid')
    partial_paid = invoices.filtered(lambda r: r.payment_state == 'partial')
    not_paid = invoices.filtered(lambda r: r.payment_state == 'not_paid')
    
    print(f"\n3. Payment Status (Invoices)")
    print(f"   - Fully Reconciled: {len(fully_paid)}")
    print(f"   - Partially Reconciled: {len(partial_paid)}")
    print(f"   - Unreconciled: {len(not_paid)}")

    # 4. Deep Dive into Unlinked Records
    if unlinked_pay:
        print(f"\n4. Critical Issues (Action Required):")
        print(f"   - {len(unlinked_pay)} payments have no accounting impact.")
    
    # Check if there are any MIG_REC moves still unlinked
    unlinked_moves = env['account.move'].search([('ref', 'like', 'MIG_REC/%'), ('origin_payment_id', '=', False)])
    if unlinked_moves:
        print(f"   - {len(unlinked_moves)} accounting moves (MIG_REC) are not linked to UI payment records.")

if __name__ == "__main__":
    audit_accounting_connections(env)
