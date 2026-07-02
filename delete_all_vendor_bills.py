
import odoo

def delete_vendor_bills():
    print("=== Deleting All Vendor Bills ===")
    
    # 1. Search for all in_invoice moves, including archived ones
    moves = env['account.move'].with_context(active_test=False).search([('move_type', '=', 'in_invoice')])
    print(f"Found {len(moves)} vendor bills to delete.")
    
    count = 0
    total = len(moves)
    
    for move in moves:
        try:
            # If posted, reset to draft
            if move.state != 'draft':
                move.button_draft()
            
            # Unlink move
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

    # 2. Also check for 'in_receipt' just in case (Receipts)
    receipts = env['account.move'].with_context(active_test=False).search([('move_type', '=', 'in_receipt')])
    if receipts:
        print(f"Found {len(receipts)} vendor receipts to delete.")
        for r in receipts:
            try:
                if r.state != 'draft':
                    r.button_draft()
                r.unlink()
            except Exception as e:
                print(f"  ✗ Failed to delete receipt {r.name}: {e}")
            
    env.cr.commit()

delete_vendor_bills()
