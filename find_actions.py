
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def find_actions():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        action_names = ['Day Book', 'Bank Book', 'Partner Ledger', 'Balance Sheet', 'Profit and Loss']
        for name in action_names:
            actions = env['ir.actions.act_window'].search([('name', 'ilike', name)])
            for a in actions:
                print(f"WINDOW ACTION: {a.name} | ID: {a.id} | MODEL: {a.res_model}")
            
            reports = env['ir.actions.report'].search([('name', 'ilike', name)])
            for r in reports:
                print(f"REPORT ACTION: {r.name} | ID: {r.id} | MODEL: {r.model}")

if __name__ == "__main__":
    find_actions()
