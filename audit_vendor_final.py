
def audit_vendor_accounting(env):
    print("=== Vendor Accounting Final Audit ===")
    
    # 1. Vendor Bills Audit
    bills = env['account.move'].search([('move_type', '=', 'in_invoice')])
    total_bills = len(bills)
    paid_bills = bills.filtered(lambda r: r.payment_state in ('paid', 'in_payment'))
    partial_bills = bills.filtered(lambda r: r.payment_state == 'partial')
    unpaid_bills = bills.filtered(lambda r: r.payment_state == 'not_paid')
    
    print(f"\n1. Vendor Bills (Total: {total_bills})")
    print(f"   - Paid: {len(paid_bills)}")
    print(f"   - Partial: {len(partial_bills)}")
    print(f"   - Unpaid: {len(unpaid_bills)}")
    
    # 2. Vendor Payments Audit
    payments = env['account.payment'].search([('partner_type', '=', 'supplier')])
    linked_pay = payments.filtered(lambda r: r.move_id)
    print(f"\n2. Vendor Payments (Total: {len(payments)})")
    print(f"   - Linked to Accounting: {len(linked_pay)}")
    
    # 3. Partners
    vendors = env['res.partner'].search([('supplier_rank', '>', 0)])
    print(f"\n3. Vendors in System: {len(vendors)}")

if __name__ == "__main__":
    audit_vendor_accounting(env)
