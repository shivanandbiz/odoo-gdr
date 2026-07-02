print("Locating modules...")
modules = env['ir.module.module'].search([('name', 'in', ['om_hr_payroll', 'payroll'])])
for mod in modules:
    print(f"{mod.name}: {mod.state}")
import odoo.modules.module as module
print("om_hr_payroll path:", module.get_module_path('om_hr_payroll'))
