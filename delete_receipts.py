import odoo

def delete_receipts():
    print("=== Deleting Receipt Register Records ===")
    
    # Identify moves with ref starting with REC/
    moves = env['account.move'].search([('ref', 'like', 'REC/%')])
    print(f"Found {len(moves)} receipt records to delete.")
    
    count = 0
    total = len(moves)
    
    for move in moves:
        try:
            if move.state != 'draft':
                move.button_draft()
            move.unlink()
            count += 1
            if count % 100 == 0:
                print(f"  ... deleted {count}/{total}")
                env.cr.commit()
        except Exception as e:
            print(f"  ✗ Failed to delete {move.name}: {e}")
            env.cr.rollback()
            
    env.cr.commit()
    print(f"\nSuccessfully deleted {count} records.")

delete_receipts()
