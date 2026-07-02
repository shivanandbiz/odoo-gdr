import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_oca_reports():
    db_name = 'Odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Check if the model exists
        if 'account.financial.report' in env:
            print("Model account.financial.report found.")
            reports = env['account.financial.report'].search([])
            for r in reports:
                print(f"Report: {r.name} (Parent: {r.parent_id.name if r.parent_id else 'None'})")
        else:
            print("Model account.financial.report NOT found.")

if __name__ == "__main__":
    check_oca_reports()
