
def check_unlinked_pairs(env):
    print("=== Checking Unlinked Invoice-Payment Pairs ===")
    
    # Find partners who have both unpaid invoices and payments
    invoices = env['account.move'].search([
        ('move_type', '=', 'out_invoice'),
        ('payment_state', 'in', ('not_paid', 'partial')),
        ('state', '=', 'posted')
    ])
    
    payments = env['account.payment'].search([
        ('partner_type', '=', 'customer'),
        ('state', '=', 'paid')
    ])
    
    partners_with_both = set(invoices.mapped('partner_id.id')) & set(payments.mapped('partner_id.id'))
    
    print(f"Partners with both unpaid invoices and payments: {len(partners_with_both)}")
    
    for pid in list(partners_with_both)[:5]:
        partner = env['res.partner'].browse(pid)
        p_invs = invoices.filtered(lambda r: r.partner_id.id == pid)
        p_pays = payments.filtered(lambda r: r.partner_id.id == pid)
        
        print(f"\nPartner: {partner.name}")
        print(f" - Unpaid Invoices: {len(p_invs)} (Total: {sum(p_invs.mapped('amount_residual'))})")
        print(f" - Payments: {len(p_pays)} (Total: {sum(p_pays.mapped('amount'))})")
        
        for inv in p_invs[:2]:
            print(f"   INV: {inv.name} | Ref: {inv.ref} | Date: {inv.invoice_date} | Residual: {inv.amount_residual}")
        for pay in p_pays[:2]:
            print(f"   PAY: {pay.name} | Memo: {pay.memo} | Date: {pay.date} | Amount: {pay.amount}")

if __name__ == "__main__":
    check_unlinked_pairs(env)
