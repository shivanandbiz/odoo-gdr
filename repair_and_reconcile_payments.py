
def match_and_reconcile(env):
    print("=== Matching MIG_REC moves with Payments ===")
    
    moves = env['account.move'].search([('ref', 'like', 'MIG_REC/%'), ('move_type', '=', 'entry')])
    payments = env['account.payment'].search([('partner_type', '=', 'customer'), ('move_id', '=', False)])
    
    print(f"Total Candidate Moves: {len(moves)}")
    print(f"Total Unlinked Payments: {len(payments)}")
    
    matched_count = 0
    reconciled_count = 0
    
    for pay in payments:
        # Match by partner, amount and date
        match = moves.filtered(lambda m: m.partner_id == pay.partner_id and abs(m.amount_total - pay.amount) < 0.01 and m.date == pay.date)
        
        if not match:
            # Try without date if not found
            match = moves.filtered(lambda m: m.partner_id == pay.partner_id and abs(m.amount_total - pay.amount) < 0.01)
        
        if match:
            # Pick the best match (closest date or first available)
            target_move = match[0]
            
            # LINK THEM
            try:
                env.cr.execute("UPDATE account_payment SET move_id = %s WHERE id = %s", (target_move.id, pay.id))
                env.cr.execute("UPDATE account_move SET origin_payment_id = %s WHERE id = %s", (pay.id, target_move.id))
                matched_count += 1
                
                # Now RECONCILE
                # Find the receivable line in the move
                pay_line = target_move.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
                
                # Find oldest open invoices for this partner
                invoices = env['account.move'].search([
                    ('partner_id', '=', pay.partner_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ('not_paid', 'partial'))
                ], order='invoice_date asc, id asc')
                
                if pay_line and invoices:
                    inv_lines = invoices.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
                    if inv_lines:
                        # Reconcile pay_line with inv_lines (Odoo will handle partials)
                        (pay_line | inv_lines).reconcile()
                        reconciled_count += 1
                        
            except Exception as e:
                print(f"Error linking/reconciling Payment {pay.id}: {e}")
                
    env.cr.commit()
    print(f"\nFinal Summary:")
    print(f" - Successfully Linked: {matched_count}")
    print(f" - Successfully Reconciled: {reconciled_count}")

if __name__ == "__main__":
    match_and_reconcile(env)
