
def impact_accounting_final(env):
    print("=== Ensuring Total Accounting Impact (Tally Sync) ===")
    
    # 1. Handle the 17 orphaned payments (Banks/Transfers)
    unlinked = env['account.payment'].search([('partner_type', '=', 'customer'), ('move_id', '=', False)])
    print(f"Found {len(unlinked)} orphaned records to impact accounting.")
    
    # We need a fallback journal
    default_journal = env['account.journal'].search([('type', '=', 'bank')], limit=1)
    suspense_account = env['account.account'].search([('name', 'ilike', 'Suspense')], limit=1)
    if not suspense_account:
        suspense_account = env['account.account'].search([('account_type', '=', 'asset_current')], limit=1)

    linked_count = 0
    for pay in unlinked:
        # Create an entry: Debit Bank, Credit Suspense (or similar)
        # to ensure the money is accounted for.
        try:
            move = env['account.move'].create({
                'move_type': 'entry',
                'date': pay.date,
                'ref': f"TALLY_SYNC/{pay.id}",
                'journal_id': pay.journal_id.id or default_journal.id,
                'line_ids': [
                    (0, 0, {
                        'name': f"Tally Impact: {pay.partner_id.name}",
                        'account_id': pay.journal_id.default_account_id.id,
                        'debit': pay.amount,
                    }),
                    (0, 0, {
                        'name': f"Tally Impact: {pay.partner_id.name}",
                        'account_id': pay.partner_id.property_account_receivable_id.id or suspense_account.id,
                        'credit': pay.amount,
                        'partner_id': pay.partner_id.id,
                    }),
                ]
            })
            move.action_post()
            
            # LINK
            env.cr.execute("UPDATE account_payment SET move_id = %s WHERE id = %s", (move.id, pay.id))
            env.cr.execute("UPDATE account_move SET origin_payment_id = %s WHERE id = %s", (pay.id, move.id))
            linked_count += 1
            
        except Exception as e:
            print(f"Error impacting account for {pay.id}: {e}")

    env.cr.commit()
    print(f"Linked {linked_count} new entries to accounting.")
    
    # 2. Re-run reconciliation for any newly enabled records
    # (Just in case some were customers)
    from repair_and_reconcile_payments_v2 import repair_and_reconcile_v2
    repair_and_reconcile_v2(env)

if __name__ == "__main__":
    impact_accounting_final(env)
