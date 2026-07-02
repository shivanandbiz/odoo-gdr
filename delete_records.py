import odoo

def delete_requested():
    print("=== Deleting Requested Records ===")
    
    # 1. Identify records
    # Credit Notes: out_refund
    # Debit Notes: in_refund (in Tally/migration context)
    # Receipt/Payment Register / Journal Entries: entry
    
    domain = [
        ('move_type', 'in', ['out_refund', 'in_refund', 'entry'])
    ]
    
    moves = env['account.move'].search(domain)
    print(f"Found {len(moves)} records to delete.")
    
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

delete_requested()
