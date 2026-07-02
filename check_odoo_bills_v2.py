
import odoo
from odoo import api, SUPERUSER_ID

def check_odoo_bills():
    odoo.tools.config.parse(args=['-c', 'odoo.conf'])
    db_name = odoo.tools.config['db_name'] or 'odoo'
    registry = odoo.registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        bills = env['account.move'].search([('move_type', '=', 'in_invoice'), ('state', '!=', 'cancel')])
        print(f"Odoo Bill Count: {len(bills)}")
        print(f"Odoo Gross Total: {sum(bills.mapped('amount_total')):,.2f}")

if __name__ == '__main__':
    check_odoo_bills()
