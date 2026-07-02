
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.tools import config

def check_1089_lambda():
    config.parse_config(['-c', 'debian/odoo.conf'])
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        view = env['ir.ui.view'].browse(1089)
        for line in view.arch_db.split('\n'):
            if 'lambda' in line:
                print(line.strip())

if __name__ == "__main__":
    check_1089_lambda()
