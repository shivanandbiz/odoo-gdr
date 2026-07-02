import odoo
from odoo import api, SUPERUSER_ID

mod = env['ir.module.module'].search([('name', '=', 'hr')])
if mod:
    print(f"Module 'hr' state is: {mod.state}")
else:
    print("Module 'hr' NOT FOUND.")
