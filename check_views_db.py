
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.tools import config

def check_views():
    config.parse_config(['-c', 'debian/odoo.conf'])
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        keys = ['account.report_invoice', 'account.report_invoice_document', 'account.report_payment_receipt_document']
        for key in keys:
            view = env['ir.ui.view'].search([('key', '=', key)], limit=1)
            if view:
                print(f"--- VIEW: {key} ---")
                print(view.arch_db)
            else:
                print(f"--- VIEW {key} NOT FOUND ---")

if __name__ == "__main__":
    check_views()
