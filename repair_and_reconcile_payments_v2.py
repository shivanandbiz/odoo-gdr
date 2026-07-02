
def repair_and_reconcile_v2(env):
    print("=== Matching MIG_REC moves with Payments (v2) ===")
    
    moves = env['account.move'].search([('ref', 'like', 'MIG_REC/%'), ('move_type', '=', 'entry')])
    payments = env['account.payment'].search([('partner_type', '=', 'customer'), ('move_id', '=', False)])
    
    print(f"Total Candidate Moves: {len(moves)}")
    print(f"Total Unlinked Payments: {len(payments)}")
    
    matched_count = 0
    reconciled_count = 0
    
    for pay in payments:
        # Match by looking into move lines
        # Amount match (using move.amount_total or sum of debits/credits)
        target_move = None
        for m in moves:
            # Check if any line has the correct partner and amount
            # Since it's a receipt, we look for a line with credit = pay.amount or debit = pay.amount
            line = m.line_ids.filtered(lambda l: l.partner_id == pay.partner_id and abs(l.debit - pay.amount) < 0.01 or abs(l.credit - pay.amount) < 0.01)
            if line and m.date == pay.date:
                target_move = m
                break
        
        if not target_move:
            # Secondary check without date
            for m in moves:
                line = m.line_ids.filtered(lambda l: l.partner_id == pay.partner_id and abs(l.debit - pay.amount) < 0.01 or abs(l.credit - pay.amount) < 0.01)
                if line:
                    target_move = m
                    break

        if target_move:
            try:
                # Link them
                env.cr.execute("UPDATE account_payment SET move_id = %s WHERE id = %s", (target_move.id, pay.id))
                env.cr.execute("UPDATE account_move SET origin_payment_id = %s, partner_id = %s WHERE id = %s", (pay.id, pay.partner_id.id, target_move.id))
                matched_count += 1
                
                # Now RECONCILE
                pay_line = target_move.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
                
                # Find open invoices
                invoices = env['account.move'].search([
                    ('partner_id', '=', pay.partner_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ('not_paid', 'partial'))
                ], order='invoice_date asc, id asc')
                
                if pay_line and invoices:
                    inv_lines = invoices.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
                    if inv_lines:
                        # Reconcile pay_line with inv_lines
                        # We use a savepoint to avoid one failure breaking the loop
                        try:
                            with env.cr.savepoint():
                                (pay_line | inv_lines).reconcile()
                                reconciled_count += 1
                        except Exception as re:
                            print(f"Reconcile error for {pay.name}: {re}")
                
            except Exception as e:
                print(f"Error processing {pay.name}: {e}")

    env.cr.commit()
    print(f"\nFinal Summary (v2):")
    print(f" - Successfully Linked: {matched_count}")
    print(f" - Successfully Reconciled: {reconciled_count}")

if __name__ == "__main__":
    repair_and_reconcile_v2(env)
