
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def find_reporting_menu():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        # Find the root reporting menu
        m = env['ir.ui.menu'].search([('name', '=', 'Reporting'), ('parent_id', '=', False)], limit=1)
        if m:
            print(f"REPORTING_ID: {m.id}")
            # Also find submenus to see where to put the new ones
            subs = env['ir.ui.menu'].search([('parent_id', '=', m.id)])
            for s in subs:
                print(f"  SUB: {s.name} | ID: {s.id}")
        else:
            print("REPORTING_ID: NOT FOUND")

if __name__ == "__main__":
    find_reporting_menu()
