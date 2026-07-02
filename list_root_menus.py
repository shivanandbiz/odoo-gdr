
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def list_root_menus():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        menus = env['ir.ui.menu'].search([('parent_id', '=', False)])
        for m in menus:
            print(f"ROOT MENU: {m.name} | ID: {m.id}")

if __name__ == "__main__":
    list_root_menus()
