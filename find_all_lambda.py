
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.tools import config

def find_all_lambda():
    config.parse_config(['-c', 'debian/odoo.conf'])
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        views = env['ir.ui.view'].search([('arch_db', 'like', '%lambda%')])
        print(f"TOTAL VIEWS WITH lambda: {len(views)}")
        for v in views:
            print(f"{v.key} ({v.id})")

if __name__ == "__main__":
    find_all_lambda()
