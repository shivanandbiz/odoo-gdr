import odoo
from odoo import api, SUPERUSER_ID

total = env['res.partner'].search_count([])
with_vat = env['res.partner'].search_count([('vat', '!=', False)])
print(f"Total Partners: {total}")
print(f"Partners with GSTIN: {with_vat}")
