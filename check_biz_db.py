import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_reports_on_biz():
    db_name = 'biz'
    conf = odoo.tools.config
    conf['db_name'] = db_name
    conf['db_user'] = 'odoo'
    conf['db_password'] = 'odoo'
    conf['db_host'] = 'localhost'
    conf['db_port'] = '5432'
    
    try:
        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            reports = env['account.report'].search([])
            for r in reports:
                print(f"DATABASE {db_name} | REPORT: {r.name}")
    except Exception as e:
        print(f"Error checking {db_name}: {e}")

if __name__ == "__main__":
    check_reports_on_biz()
