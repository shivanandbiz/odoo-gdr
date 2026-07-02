import odoo
from odoo import api, SUPERUSER_ID

mods = env['ir.module.module'].search([('name', '=like', 'l10n_in%')])
for m in mods:
    print(f"Module: {m.name: <30} State: {m.state}")
