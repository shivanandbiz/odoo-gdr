
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.tools import config

def check_1089():
    config.parse_config(['-c', 'debian/odoo.conf'])
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        view = env['ir.ui.view'].browse(1089)
        print(f"VIEW ID: {view.id}")
        print(f"VIEW KEY: {view.key}")
        print(view.arch_db)

if __name__ == "__main__":
    check_1089()
