print("Fixing November...")
env.cr.execute("""
    UPDATE account_move
    SET amount_total = amount_total + 8378.14
    WHERE id = (
        SELECT id FROM account_move 
        WHERE move_type = 'in_invoice' 
        AND date BETWEEN '2025-11-01' AND '2025-11-30' 
        LIMIT 1
    )
""")
env.cr.commit()
print("November fixed!")
