import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_modules():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        mods = env['ir.module.module'].search([('name', 'like', 'om_'), ('state', '=', 'installed')])
        for m in mods:
            print(f"MODULE: {m.name} | STATE: {m.state}")
            
        # Check specific modules
        mod_names = ['accounting_pdf_reports', 'om_account_accountant']
        for name in mod_names:
            m = env['ir.module.module'].search([('name', '=', name)])
            print(f"MODULE: {name} | STATE: {m.state if m else 'NOT FOUND'}")

if __name__ == "__main__":
    check_modules()
