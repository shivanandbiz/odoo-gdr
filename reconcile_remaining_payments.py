
def reconcile_remaining(env):
    # Search for posted customer payments that are not reconciled
    payments = env['account.payment'].search([
        ('state', '=', 'posted'),
        ('is_reconciled', '=', False),
        ('payment_type', '=', 'inbound'),
        ('partner_type', '=', 'customer')
    ])
    print(f"Found {len(payments)} unreconciled customer payments.")
    
    count = 0
    for p in payments:
        if not p.partner_id:
            continue
            
        # Get the receivable line from the payment's move
        rec_line = p.move_id.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
        
        if not rec_line:
            continue
            
        # Search for open customer invoices for this partner
        invoices = env['account.move'].search([
            ('partner_id', '=', p.partner_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial'))
        ], order='date asc')
        
        if not invoices:
            # Try searching by partner name variations if no invoices found for exact ID
            # (In case there are duplicate partners)
            similar_partners = env['res.partner'].search([('name', 'ilike', p.partner_id.name)])
            if len(similar_partners) > 1:
                invoices = env['account.move'].search([
                    ('partner_id', 'in', similar_partners.ids),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ('not_paid', 'partial'))
                ], order='date asc')

        if invoices:
            inv_lines = invoices.mapped('line_ids').filtered(lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
            if inv_lines:
                print(f"Reconciling Payment {p.name} ($ {p.amount}) for Partner {p.partner_id.name} with {len(invoices)} invoices.")
                try:
                    (rec_line | inv_lines).reconcile()
                    count += 1
                except Exception as e:
                    print(f"  Error reconciling {p.name}: {e}")
        else:
            print(f"No open invoices found for Partner {p.partner_id.name} (Payment {p.name})")

    env.cr.commit()
    print(f"Successfully reconciled {count} more payments.")

if __name__ == "__main__":
    reconcile_remaining(env)
