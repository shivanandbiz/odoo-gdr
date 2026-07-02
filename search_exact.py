
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.tools import config

def search_exact_string():
    config.parse_config(['-c', 'debian/odoo.conf'])
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        target = 'any([l.discount for l in o.invoice_line_ids])'
        views = env['ir.ui.view'].search([('arch_db', 'like', f'%{target}%')])
        print(f"FOUND {len(views)} VIEWS WITH EXACT STRING")
        for v in views:
            print(f"{v.key} ({v.id})")

if __name__ == "__main__":
    search_exact_string()
