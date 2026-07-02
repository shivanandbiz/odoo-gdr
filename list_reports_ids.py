import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_all_reports_ids():
    conf = odoo.tools.config
    conf['db_name'] = 'Odoo'
    conf['db_user'] = 'odoo'
    conf['db_password'] = 'odoo'
    conf['db_host'] = 'localhost'
    conf['db_port'] = '5432'
    
    registry = Registry('Odoo')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        reports = env['account.report'].search([])
        for r in reports:
            xml_id = r.get_external_id().get(r.id)
            print(f"REPORT: {r.name} | XML_ID: {xml_id}")

if __name__ == "__main__":
    check_all_reports_ids()
