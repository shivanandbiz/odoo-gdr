import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_oca_reports():
    # Force settings
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
        
        # Check models
        models = ['account.financial.report', 'account.report', 'account.report.line']
        for m in models:
            if m in env:
                print(f"Model {m} found.")
                # If we find a report, list them
                recs = env[m].search([])
                for r in recs:
                    if hasattr(r, 'name'):
                        print(f"  {m}: {r.name}")
            else:
                print(f"Model {m} NOT found.")

if __name__ == "__main__":
    check_oca_reports()
