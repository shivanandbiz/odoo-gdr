
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
import sys

def install_custom_module(module_name):
    db_name = 'odoo'
    # Force loading of addons
    odoo.tools.config['addons_path'] = '/home/ubuntu/odoo-gdr/addons,/home/ubuntu/odoo-gdr/odoo/addons,/home/ubuntu/odoo-gdr/oca_addons/account-reconcile,/home/ubuntu/odoo-gdr/oca_addons/bank-statement-import,/home/ubuntu/odoo-gdr/oca_addons/server-tools,/home/ubuntu/odoo-gdr/dummy_modules'
    
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        print("Updating module list...")
        env['ir.module.module'].update_list()
        
        module = env['ir.module.module'].search([('name', '=', module_name)])
        if module:
            print(f"Module state: {module.state}")
            if module.state == 'installed':
                print(f"Upgrading module {module_name}...")
                module.button_immediate_upgrade()
            else:
                print(f"Installing module {module_name}...")
                module.button_immediate_install()
            cr.commit()
            print(f"Module {module_name} processed successfully.")
        else:
            print(f"Module {module_name} NOT FOUND.")

if __name__ == "__main__":
    install_custom_module('custom_credit_debit_note')
