
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.tools import config

def find_problematic_views():
    config.parse_config(['-c', 'debian/odoo.conf'])
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        views = env['ir.ui.view'].search([('arch_db', 'like', '%any(%for%')])
        print(f"FOUND {len(views)} VIEWS")
        for v in views:
            print(f"--- {v.key} ({v.id}) ---")
            # Print only lines with any(
            for line in v.arch_db.split('\n'):
                if 'any(' in line and 'for' in line:
                    print(line.strip())

if __name__ == "__main__":
    find_problematic_views()
