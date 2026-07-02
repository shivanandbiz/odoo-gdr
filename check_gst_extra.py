import odoo
from odoo import api, SUPERUSER_ID

mods = env['ir.module.module'].search([('name', 'ilike', 'gst'), ('state', '=', 'uninstalled')])
for m in mods:
    print(f"Module (GST): {m.name: <30} State: {m.state}")

mods_tax = env['ir.module.module'].search([('name', '=like', 'l10n_in_%'), ('state', '=', 'uninstalled')])
for m in mods_tax:
    print(f"Module (L10N_IN): {m.name: <30} State: {m.state}")
