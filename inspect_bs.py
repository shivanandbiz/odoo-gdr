import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def fix_balance_sheet():
    odoo.tools.config.parse(['-c', '/home/biz/odoo/odoo.conf'])
    db_name = odoo.tools.config['db_name']
    
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Find the Balance Sheet report
        report = env['account.report'].search([('name', '=', 'Balance Sheet')], limit=1)
        if not report:
            print("Balance Sheet report not found!")
            return

        print(f"Found report: {report.name} (ID: {report.id})")
        
        # We need to restructure the lines. 
        # For simplicity, we'll try to find the lines and update their names/parents.
        
        # Desired structure:
        # ASSETS
        #   Current Assets
        #     Bank and Cash Accounts
        #     Receivables
        #     Current Assets
        #     Prepayments
        #   Plus Fixed Assets
        #   Plus Non-current Assets
        # LIABILITIES
        #   Current Liabilities
        #     Current Liabilities
        #     Payables
        #   Plus Non-current Liabilities
        # EQUITY
        #   Unallocated Earnings

        # Since I don't know the exact current state, I will just list them first.
        lines = env['account.report.line'].search([('report_id', '=', report.id)], order='sequence')
        for l in lines:
            print(f"Line ID: {l.id}, Name: {l.name}, Parent: {l.parent_id.name if l.parent_id else 'None'}, Sequence: {l.sequence}")

if __name__ == "__main__":
    fix_balance_sheet()
