
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def install_custom_module():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        env['ir.module.module'].update_list()
        
        module_name = 'custom_accounting_reports'
        module = env['ir.module.module'].search([('name', '=', module_name)])
        if module:
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
    install_custom_module()
