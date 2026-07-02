import odoo
from odoo import api, SUPERUSER_ID

mod = env['ir.module.module'].search([('name', '=', 'sign')])
if mod:
    print(f"Module 'sign' state is: {mod.state}")
else:
    print("Module 'sign' NOT FOUND.")
