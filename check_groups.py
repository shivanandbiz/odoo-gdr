import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_groups():
    # Set up config manually to avoid the parse error
    conf = odoo.tools.config
    conf['db_name'] = 'Odoo'
    conf['db_user'] = 'odoo'
    conf['db_password'] = 'odoo'
    conf['db_host'] = 'localhost'
    conf['db_port'] = '5432'
    
    registry = Registry('Odoo')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        groups = env['account.group'].search([], order='code_prefix_start')
        for g in groups:
            print(f"Group: {g.name} (Code: {g.code_prefix_start}, Parent: {g.parent_id.name if g.parent_id else 'None'})")

if __name__ == "__main__":
    check_groups()
