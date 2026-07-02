import odoo
from odoo import api, SUPERUSER_ID

modules_to_install = ['hr_expense', 'hr_timesheet']
print(f"Installing: {modules_to_install}")

mods = env['ir.module.module'].search([('name', 'in', modules_to_install), ('state', '=', 'uninstalled')])
if mods:
    mods.button_immediate_install()
    env.cr.commit()
    print("Installation successful.")
else:
    print("Modules already installed or missing.")
