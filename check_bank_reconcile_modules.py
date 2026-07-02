
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_modules():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        modules_to_check = [
            'account_reconcile_oca',
            'account_statement_base',
            'account_statement_import_file',
            'account_statement_import_camt',
        ]
        for mod_name in modules_to_check:
            module = env['ir.module.module'].search([('name', '=', mod_name)])
            if module:
                print(f"Module {mod_name}: State={module.state}")
            else:
                print(f"Module {mod_name}: NOT FOUND in DB")

if __name__ == "__main__":
    check_modules()
