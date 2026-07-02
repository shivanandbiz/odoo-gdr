print("Undo Payment/Receipt from V4")
moves = env['account.move'].search([
    '|', '|',
    ('ref', 'like', 'Payment%'),
    ('ref', 'like', 'Receipt%'),
    ('ref', 'like', 'PAY_%')
])
if moves:
    print(f"Deleting {len(moves)} generic moves...")
    moves.button_draft()
    moves.unlink()

# also clean the ones from today
env.cr.execute("DELETE FROM account_partial_reconcile")
env.cr.execute("DELETE FROM account_full_reconcile")
env.cr.execute("DELETE FROM account_payment WHERE memo LIKE 'PAY_MIG%%' OR memo LIKE 'REC_MIG%%'")
env.cr.commit()
print("Done")
