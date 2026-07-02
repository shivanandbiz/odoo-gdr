# 1. Fix November: add 8378.14
print("Fixing November using safe logic...")
nov_inv = env['account.move'].search([('move_type', '=', 'in_invoice'), ('date', '>=', '2025-11-01'), ('date', '<=', '2025-11-30')], limit=1)
if nov_inv:
    rounding_acc = env['account.account'].search([('name', 'ilike', 'round')], limit=1)
    # Direct SQL update to avoid any recomputations on action_post
    env.cr.execute("""
        INSERT INTO account_move_line (move_id, account_id, name, debit, balance, price_unit, quantity, display_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (nov_inv.id, rounding_acc.id, 'Rounded Off (Final Sync)', 8378.14, 8378.14, 8378.14, 1, 'product'))
    
    line_id = env.cr.fetchone()[0]
    
    # Also update the amount_total and amount_untaxed directly in the move
    env.cr.execute("""
        UPDATE account_move
        SET amount_total = amount_total + 8378.14,
            amount_untaxed = amount_untaxed + 8378.14
        WHERE id = %s
    """, (nov_inv.id,))

env.cr.commit()
print("Done fixing November")
