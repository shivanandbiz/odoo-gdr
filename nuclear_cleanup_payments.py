print("--- NUCLEAR CLEANUP OF PAYMENTS AND RECEIPTS ---")

def cleanup():
    # 1. Unreconcile all completely to prevent foreign key errors
    env.cr.execute("DELETE FROM account_partial_reconcile")
    env.cr.execute("DELETE FROM account_full_reconcile")
    
    # 2. Clear all account.payment records
    payments = env['account.payment'].search([])
    if payments:
        print(f"  Deleting {len(payments)} payment records...")
        payments.action_draft()
        payments.unlink()

    # 3. Clear Moves with common migration prefixes related to payments/receipts
    prefixes = ['REC/', 'PAY/', 'PAY_GDR/', 'PAY_JAN_MAR/', 'PAY_OCT_DEC/', 'AJ/', 'JS/', 'OD/', 'JM/', 'PAY_MIG/', 'REC_MIG/', 'Payment', 'Receipt']
    for pref in prefixes:
        moves = env['account.move'].search([('ref', 'like', f"{pref}%")])
        if moves:
            print(f"  Deleting {len(moves)} moves with prefix '{pref}'...")
            moves.button_draft()
            moves.unlink()
    
    # Also clean up moves that have generic formatting from scripts if any remain
    ghost_moves = env['account.move'].search([
        ('move_type', '=', 'entry'),
        ('date', '>=', '2025-04-01'),
        ('date', '<=', '2026-03-31'),
        '|',
        ('ref', 'ilike', 'Payment%'),
        ('ref', 'ilike', 'Receipt%')
    ])
    if ghost_moves:
        print(f"  Deleting {len(ghost_moves)} ghost journal entries...")
        ghost_moves.button_draft()
        ghost_moves.unlink()

    env.cr.commit()
    print("Cleanup SUCCESS. The Odoo GUI should now be empty of all vendor/customer payments.")

cleanup()
