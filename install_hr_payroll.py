import sys
import os

os.chdir('/home/ubuntu/odoo-gdr')
sys.path.append('/home/ubuntu/odoo-gdr')

import odoo

def main():
    odoo.tools.config.parse_config(['-c', 'debian/odoo.conf'])
    registry = odoo.registry('odoo')
    with odoo.api.Environment.manage(), registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        
        # Update app list
        print("Updating module list...")
        env['ir.module.module'].update_list()
        
        # Search for HR and Payroll modules
        modules = env['ir.module.module'].search([('name', 'ilike', 'payroll')])
        print(f"Found payroll modules: {modules.mapped('name')}")
        
        modules_to_install = ['hr']
        
        # Prefer om_hr_payroll or hr_payroll
        if 'om_hr_payroll' in modules.mapped('name'):
            modules_to_install.append('om_hr_payroll')
        elif 'hr_payroll' in modules.mapped('name'):
            modules_to_install.append('hr_payroll')
        else:
            if modules:
                modules_to_install.append(modules[0].name)
            else:
                print("No payroll module found.")
        
        print(f"Modules to install: {modules_to_install}")
        
        modules = env['ir.module.module'].search([('name', 'in', modules_to_install)])
        
        found_names = modules.mapped('name')
        missing = set(modules_to_install) - set(found_names)
        if missing:
            print(f"Warning: The following modules were not found: {missing}")
            
        uninstalled = modules.filtered(lambda m: m.state != 'installed')
        if not uninstalled:
            print("All requested modules are already installed.")
            return

        print(f"To install: {uninstalled.mapped('name')}")
        uninstalled.button_immediate_install()
        print("Setting state to installed...")

        env.cr.commit()
        print("Finished.")

if __name__ == '__main__':
    main()
