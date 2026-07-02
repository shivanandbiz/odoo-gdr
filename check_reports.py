import odoo
from odoo import api, SUPERUSER_ID

def check_reports():
    conf = odoo.tools.config
    conf['db_name'] = 'Odoo'
    conf['db_user'] = 'odoo'
    conf['db_password'] = 'odoo'
    conf['db_host'] = 'localhost'
    conf['db_port'] = '5432'
    
    registry = odoo.registry('Odoo')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        reports = env['account.report'].search([])
        for r in reports:
            print(f"Report: {r.name} (ID: {r.id})")
            if 'Balance Sheet' in r.name:
                lines = env['account.report.line'].search([('report_id', '=', r.id)], order='sequence')
                for l in lines:
                    print(f"  Line: {l.name} (Code: {l.code}, Parent: {l.parent_id.name if l.parent_id else 'None'})")

if __name__ == "__main__":
    check_reports()
