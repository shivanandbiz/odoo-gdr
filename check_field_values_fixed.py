
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.tools import config

def check_field_values():
    db_name = 'odoo'
    # Load config from the file
    config.parse_config(['-c', 'debian/odoo.conf'])
    
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        journal = env['account.journal'].new()
        options = journal._get_bank_statements_available_sources()
        print(f"Selection options values: {options}")

if __name__ == "__main__":
    check_field_values()
