try:
    print("Starting SQL Cleanup...")
    env.cr.execute("UPDATE account_move SET origin_payment_id = NULL")
    env.cr.execute("DELETE FROM account_partial_reconcile")
    env.cr.execute("DELETE FROM account_full_reconcile")
    env.cr.execute("DELETE FROM account_payment")
    env.cr.execute("DELETE FROM account_move_line WHERE move_id IN (SELECT id FROM account_move WHERE ref LIKE 'PAY_%%')")
    env.cr.execute("DELETE FROM account_move WHERE ref LIKE 'PAY_%%'")
    env.cr.commit()
    print("Cleanup SUCCESS")
except Exception as e:
    print(f"Cleanup Failed: {e}")
    env.cr.rollback()
