import odoo
from odoo import api, SUPERUSER_ID

mods = env['ir.module.module'].search([('name', '=like', 'hr_%')])
for m in mods:
    print(f"Module: {m.name: <25} State: {m.state}")
