
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.tools import config

def check_view():
    config.parse_config(['-c', 'debian/odoo.conf'])
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        view = env['ir.ui.view'].search([('key', '=', 'account.report_invoice_document')], limit=1)
        if view:
            print(f"VIEW FOUND: {view.id}")
            print(view.arch_db)
        else:
            print("VIEW NOT FOUND")

if __name__ == "__main__":
    check_view()
