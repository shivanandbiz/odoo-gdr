import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def fix_balance_sheet():
    # Force settings
    db_name = 'Odoo'
    odoo.tools.config['db_name'] = db_name
    odoo.tools.config['db_user'] = 'odoo'
    odoo.tools.config['db_password'] = 'odoo'
    odoo.tools.config['db_host'] = 'localhost'
    odoo.tools.config['db_port'] = '5432'
    
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Find the Balance Sheet report
        report = env['account.report'].search([('name', '=', 'Balance Sheet')], limit=1)
        if not report:
            print("Balance Sheet report not found!")
            return

        print(f"REPORT_ID: {report.id}")
        
        lines = env['account.report.line'].search([('report_id', '=', report.id)], order='sequence')
        for l in lines:
            # Output in a parsable format
            print(f"LINE|{l.id}|{l.name}|{l.parent_id.id if l.parent_id else 'None'}|{l.sequence}")

if __name__ == "__main__":
    fix_balance_sheet()
