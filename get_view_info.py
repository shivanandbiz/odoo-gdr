
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.tools import config

def get_view_info():
    config.parse_config(['-c', 'debian/odoo.conf'])
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        view = env['ir.ui.view'].search([('key', '=', 'account.report_invoice_document')], limit=1)
        print(f"ID: {view.id}")
        print(f"KEY: {view.key}")
        print(f"NAME: {view.name}")
        # Grep for any( in arch_db
        for i, line in enumerate(view.arch_db.split('\n')):
            if 'any(' in line:
                print(f"L{i+1}: {line.strip()}")

if __name__ == "__main__":
    get_view_info()
