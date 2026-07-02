import odoo
from odoo import api, SUPERUSER_ID

def check():
    conf_file = '/home/biz/odoo/odoo.conf'
    odoo.tools.config.parse_config(['-c', conf_file])
    registry = odoo.registry(odoo.tools.config['db_name'])
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        a_1m = env['account.account'].search([('code', '=', '1000000')])
        a_400k = env['account.account'].search([('code', '=', '400000')])
        print(f"Code 1000000: {a_1m.name} ({a_1m.account_type}) if a_1m else 'NOT FOUND'")
        print(f"Code 400000: {a_400k.name} ({a_400k.account_type}) if a_400k else 'NOT FOUND'")

if __name__ == '__main__':
    check()
