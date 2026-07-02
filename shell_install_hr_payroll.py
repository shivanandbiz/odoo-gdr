# Update app list
print("Updating module list...")
env['ir.module.module'].update_list()

# Search for HR and Payroll modules
modules = env['ir.module.module'].search([('name', 'ilike', 'payroll')])
print(f"Found payroll modules: {modules.mapped('name')}")

modules_to_install = ['hr', 'payroll']

print(f"Modules to install: {modules_to_install}")

modules = env['ir.module.module'].search([('name', 'in', modules_to_install)])

found_names = modules.mapped('name')
missing = set(modules_to_install) - set(found_names)
if missing:
    print(f"Warning: The following modules were not found: {missing}")
    
uninstalled = modules.filtered(lambda m: m.state != 'installed')
if not uninstalled:
    print("All requested modules are already installed.")
else:
    print(f"To install: {uninstalled.mapped('name')}")
    uninstalled.button_immediate_install()
    print("Setting state to installed...")

env.cr.commit()
print("Finished.")
