
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_arch():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        view = env['ir.ui.view'].browse(3522)
        print(f"View Name: {view.name}")
        print(f"View Module: {view.xml_id}")
        print("View Arch:")
        print(view.arch)

if __name__ == "__main__":
    check_arch()
