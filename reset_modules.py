
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def reset_modules():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        mods = env['ir.module.module'].search([('state', 'in', ['to install', 'to upgrade', 'to remove'])])
        if mods:
            print(f"Found stuck modules: {[ (m.name, m.state) for m in mods ]}")
            for m in mods:
                if m.state == 'to install':
                    m.state = 'uninstalled'
                elif m.state == 'to upgrade':
                    m.state = 'installed'
                elif m.state == 'to remove':
                    m.state = 'installed'
            cr.commit()
            print("Modules reset successfully.")
        else:
            print("No stuck modules found.")

if __name__ == "__main__":
    reset_modules()
