
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def list_users():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        users = env['res.users'].search([])
        for u in users:
            print(f"USER: {u.login} | NAME: {u.name}")

if __name__ == "__main__":
    list_users()
