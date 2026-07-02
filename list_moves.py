import odoo

def list_all_moves():
    print("=== All Remaining Account Moves ===")
    moves = env['account.move'].search([])
    print(f"Total moves: {len(moves)}")
    
    types = {}
    for m in moves:
        types[m.move_type] = types.get(m.move_type, 0) + 1
        
    for t, c in types.items():
        print(f"  Type {t}: {c}")
        
    print("\nSample References (first 20):")
    for m in moves[:20]:
        print(f"  {m.name} | {m.ref} | {m.move_type}")

list_all_moves()
