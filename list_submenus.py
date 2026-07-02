
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def list_submenus(parent_id):
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        menus = env['ir.ui.menu'].search([('parent_id', '=', parent_id)])
        for m in menus:
            print(f"SUB MENU: {m.name} | ID: {m.id}")

if __name__ == "__main__":
    list_submenus(130) # Invoicing
