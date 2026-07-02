
def aggressive_reconcile(env):
    # Find all customer payments not reconciled
    payments = env['account.payment'].search([
        ('state', '=', 'posted'),
        ('is_reconciled', '=', False),
        ('payment_type', '=', 'inbound')
    ])
    print(f"Total unreconciled customer payments: {len(payments)}")
    
    reconciled_count = 0
    for p in payments:
        if not p.partner_id:
            continue
            
        # Get receivable line from payment move
        pay_line = p.move_id.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
        if not pay_line:
            continue
            
        # Search for all open invoices for this partner
        invoices = env['account.move'].search([
            ('partner_id', '=', p.partner_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial'))
        ], order='date asc')
        
        if invoices:
            inv_lines = invoices.mapped('line_ids').filtered(lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
            if inv_lines:
                print(f"Reconciling Payment {p.name} ({p.amount}) for {p.partner_id.name}")
                try:
                    (pay_line | inv_lines).reconcile()
                    reconciled_count += 1
                except Exception as e:
                    print(f"  Failed: {e}")
            else:
                print(f"No receivable lines for {p.partner_id.name} invoices.")
        else:
            # print(f"No open invoices for {p.partner_id.name}")
            pass

    env.cr.commit()
    print(f"Reconciliation session finished. Newly reconciled: {reconciled_count}")

if __name__ == "__main__":
    aggressive_reconcile(env)
