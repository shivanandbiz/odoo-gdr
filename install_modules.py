import sys
import os

# Ensure we're in the right directory
os.chdir('/home/biz/odoo')
sys.path.append('/home/biz/odoo')

import odoo

def main():
    odoo.tools.config.parse_config(['-c', 'odoo.conf'])
    registry = odoo.registry('Odoo')
    with odoo.api.Environment.manage(), registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        
        modules_to_install = [
            'om_account_accountant',
            'om_account_asset',
            'om_account_budget',
            'accounting_pdf_reports',
            'account_financial_reporting',
            'l10n_in',
            'l10n_in_ewaybill',
            'web_responsive'
        ]
        
        # Update app list
        print("Updating module list...")
        env['ir.module.module'].update_list()
        
        modules = env['ir.module.module'].search([('name', 'in', modules_to_install)])
        
        # Check if all modules were found
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
