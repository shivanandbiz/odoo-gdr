import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_accounting_report():
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
        if 'accounting.report' in env:
            print("Model accounting.report found.")
            # Check for records
            recs = env['accounting.report'].search([])
            for r in recs:
                print(f"REPORT: {r.name} | ID: {r.id}")
        else:
            print("Model accounting.report NOT found.")

if __name__ == "__main__":
    check_accounting_report()
