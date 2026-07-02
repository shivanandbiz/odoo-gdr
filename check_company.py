import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_company():
    conf = odoo.tools.config
    conf['db_name'] = 'Odoo'
    conf['db_user'] = 'odoo'
    conf['db_password'] = 'odoo'
    conf['db_host'] = 'localhost'
    conf['db_port'] = '5432'
    
    registry = Registry('Odoo')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        company = env['res.company'].search([], limit=1)
        print(f"Company: {company.name}")

if __name__ == "__main__":
    check_company()
