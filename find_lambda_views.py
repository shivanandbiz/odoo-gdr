
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.tools import config

def find_lambda_views():
    config.parse_config(['-c', 'debian/odoo.conf'])
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        views = env['ir.ui.view'].search([('arch_db', 'like', '%lambda%')])
        print(f"FOUND {len(views)} VIEWS WITH lambda")
        for v in views:
            if 'account' in v.key or 'report' in v.key:
                print(f"--- {v.key} ({v.id}) ---")
                for line in v.arch_db.split('\n'):
                    if 'lambda' in line:
                        print(line.strip())

if __name__ == "__main__":
    find_lambda_views()
