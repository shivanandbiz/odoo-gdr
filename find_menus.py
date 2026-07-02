
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def find_menus():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        menu_names = ['Day Book', 'Cash Book', 'Bank Book', 'Balance Sheet', 'Profit and Loss', 'Partner Ledger']
        for name in menu_names:
            menus = env['ir.ui.menu'].search([('name', 'ilike', name)])
            for m in menus:
                xml_id = m.get_external_id().get(m.id, 'NONE')
                action_name = m.action.name if m.action else 'NONE'
                print(f"MENU: {m.name} | ID: {m.id} | XMLID: {xml_id} | ACTION: {action_name}")

if __name__ == "__main__":
    find_menus()
