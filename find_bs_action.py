import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_actions():
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
        
        # Search actions
        actions = env['ir.actions.actions'].search([('name', 'ilike', 'Balance Sheet')])
        for a in actions:
            print(f"ACTION: {a.name} | MODEL: {a.type} | ID: {a.id}")
            if a.type == 'ir.actions.client':
                print(f"  Tag: {a.tag}")

if __name__ == "__main__":
    check_actions()
