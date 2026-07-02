import odoo
from odoo import api, SUPERUSER_ID
from odoo.tools import config

def install_modules():
    # Load configuration
    config.parse_config(['-c', '/var/www/shivodoo/debian/odoo.conf', '-d', 'shivodoo_db'])
    
    import odoo.modules.registry
    registry = odoo.modules.registry.Registry.new('shivodoo_db')
    
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        print("Updating Apps List...")
        env['ir.module.module'].update_list()
        
        modules = env['ir.module.module'].search([('name', 'in', ['multi_bill_payment', 'multi_invoice_payment'])])
        if modules:
            print(f"Found modules: {modules.mapped('name')}")
            for module in modules:
                if module.state != 'installed':
                    print(f"Installing {module.name}...")
                    module.button_immediate_install()
            print("Installation complete!")
        else:
            print("Modules not found in the database even after updating list.")
        
        env.cr.commit()

if __name__ == '__main__':
    install_modules()
