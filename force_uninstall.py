import odoo
from odoo import api, SUPERUSER_ID
from odoo.tools import config

def uninstall_module():
    # Load configuration
    config.parse_config(['-c', '/var/www/shivodoo/debian/odoo.conf', '-d', 'shivodoo_db'])
    
    import odoo.modules.registry
    registry = odoo.modules.registry.Registry.new('shivodoo_db')
    
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # 1. Force uninstall gdr_bulk_payments
        module = env['ir.module.module'].search([('name', '=', 'gdr_bulk_payments')])
        if module:
            print(f"Module state: {module.state}")
            if module.state != 'uninstalled':
                print("Uninstalling gdr_bulk_payments...")
                module.button_immediate_uninstall()
                print("Uninstalled successfully.")
            else:
                print("Module already uninstalled.")
        
        # 2. Cleanup any dangling ir.model or ir.actions that reference gdr.bulk.payment
        models = env['ir.model'].search([('model', '=', 'gdr.bulk.payment')])
        if models:
            print(f"Deleting dangling models: {models.mapped('model')}")
            models.unlink()
            
        actions = env['ir.actions.act_window'].search([('res_model', '=', 'gdr.bulk.payment')])
        if actions:
            print(f"Deleting dangling actions: {actions.mapped('name')}")
            actions.unlink()
            
        views = env['ir.ui.view'].search([('model', '=', 'gdr.bulk.payment')])
        if views:
            print(f"Deleting dangling views: {views.mapped('name')}")
            views.unlink()
            
        env.cr.commit()

if __name__ == '__main__':
    uninstall_module()
