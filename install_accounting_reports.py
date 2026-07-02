
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def install_accounting_reports():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        modules_to_install = [
            'om_account_accountant',
            'accounting_pdf_reports'
        ]
        
        for module_name in modules_to_install:
            module = env['ir.module.module'].search([('name', '=', module_name)])
            if module:
                if module.state == 'installed':
                    print(f"Module {module_name} is already installed.")
                else:
                    print(f"Installing module {module_name}...")
                    module.button_immediate_install()
                    cr.commit()
                    print(f"Module {module_name} installed successfully.")
            else:
                print(f"Module {module_name} NOT FOUND.")

if __name__ == "__main__":
    install_accounting_reports()
