
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_bank_journals():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        journals = env['account.journal'].search([('type', '=', 'bank')])
        for j in journals:
            # Check bank_statements_source field
            # In some versions it might be different, let's see if it exists
            source = getattr(j, 'bank_statements_source', 'FIELD NOT FOUND')
            print(f"Journal: {j.name} (ID: {j.id}), Source: {source}")

if __name__ == "__main__":
    check_bank_journals()
