import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_lines():
    db_name = 'Odoo'
    conf = odoo.tools.config
    conf['db_name'] = db_name
    conf['db_user'] = 'odoo'
    conf['db_password'] = 'odoo'
    conf['db_host'] = 'localhost'
    conf['db_port'] = '5432'
    
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        lines = env['account.report.line'].search([('name', 'ilike', 'Asset')])
        for l in lines:
            print(f"REPORT: {l.report_id.name} | LINE: {l.name} | ID: {l.id}")

if __name__ == "__main__":
    check_lines()
