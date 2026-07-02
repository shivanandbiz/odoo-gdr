
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_menus():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        # Search for reconciliation menus
        menus = env['ir.ui.menu'].search([('name', 'ilike', 'Reconcile')])
        for menu in menus:
            print(f"Menu: {menu.name} (ID: {menu.id}, Parent: {menu.parent_id.name if menu.parent_id else 'None'})")

if __name__ == "__main__":
    check_menus()
