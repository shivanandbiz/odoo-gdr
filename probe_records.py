import odoo

def probe():
    print("=== Odoo Record Count Probe ===")
    
    # Check move types
    move_types = env['account.move'].read_group([], ['move_type'], ['move_type'])
    print("\nAccount Move Counts by Type:")
    for mt in move_types:
        print(f"  {mt['move_type']}: {mt['move_type_count']}")
        
    # Check journal names and codes
    journals = env['account.journal'].search([])
    print("\nJournals:")
    for j in journals:
        count = env['account.move'].search_count([('journal_id', '=', j.id)])
        print(f"  {j.name} ({j.code}, {j.type}): {count} moves")

probe()
