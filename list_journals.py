import odoo

def list_journals():
    print("=== Odoo Journals ===")
    journals = env['account.journal'].search([])
    for j in journals:
        print(f"  {j.name} ({j.code}, {j.type})")

list_journals()
