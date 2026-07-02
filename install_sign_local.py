import odoo
from odoo import api, SUPERUSER_ID

mod = env['ir.module.module'].search([('name', '=', 'sign')])
if not mod:
    print("Module 'sign' NOT FOUND in local Odoo.")
else:
    if mod.state == 'installed':
        print("Module 'sign' is already INSTALLED.")
    else:
        print("Installing module 'sign'...")
        mod.button_immediate_install()
        env.cr.commit()
        print("Installed 'sign' successfully.")
