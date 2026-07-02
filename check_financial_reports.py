import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_account_financial_report():
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
        if 'account.financial.report' in env:
            print("Model account.financial.report found.")
            reports = env['account.financial.report'].search([], order='sequence')
            for r in reports:
                print(f"ID: {r.id} | Name: {r.name} | Parent: {r.parent_id.name if r.parent_id else 'None'} | Sequence: {r.sequence}")
        else:
            print("Model account.financial.report NOT found.")

if __name__ == "__main__":
    check_account_financial_report()
