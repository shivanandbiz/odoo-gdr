print("--- NUCLEAR CLEANUP OF MIGRATED DATA ---")

def cleanup():
    # 1. Clear Payments table (Since all of them were today's experiment)
    payments = env['account.payment'].search([])
    if payments:
        print(f"  Deleting {len(payments)} payment records...")
        payments.action_draft()
        payments.unlink()

    # 2. Clear Moves with common migration prefixes
    prefixes = ['REC/', 'PAY/', 'PAY_GDR/', 'PAY_JAN_MAR/', 'PAY_OCT_DEC/', 'AJ/', 'JS/', 'OD/', 'JM/', 'MIG/']
    for pref in prefixes:
        moves = env['account.move'].search([('ref', 'like', f"{pref}%")])
        if moves:
            print(f"  Deleting {len(moves)} moves with prefix {pref}...")
            moves.button_draft()
            moves.unlink()
    
    # Also clean up moves that have generic refs like "Payment 123" if they were created by scripts
    ghost_moves = env['account.move'].search([
        ('date', '>=', '2025-04-01'),
        ('date', '<=', '2026-03-31'),
        ('move_type', '=', 'entry'),
        ('ref', '=', False)
    ])
    if ghost_moves:
        print(f"  Deleting {len(ghost_moves)} ghost journal entries...")
        ghost_moves.button_draft()
        ghost_moves.unlink()

    env.cr.commit()
    print("Cleanup SUCCESS.")

cleanup()
