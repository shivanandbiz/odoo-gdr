import odoo
from odoo import api, SUPERUSER_ID

Model = env['res.partner']
print(f"Fields on {Model._name}: {list(Model._fields.keys())}")
