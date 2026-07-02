import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_bs_action_details():
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
        action = env['ir.actions.act_window'].browse(701)
        print(f"Action Name: {action.name}")
        print(f"Res Model: {action.res_model}")
        print(f"View Mode: {action.view_mode}")
        print(f"Context: {action.context}")
        print(f"Domain: {action.domain}")

if __name__ == "__main__":
    check_bs_action_details()
