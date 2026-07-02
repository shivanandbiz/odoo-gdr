import odoo
from odoo import api, SUPERUSER_ID

Model = env['account.account']
print(f"Fields on {Model._name}: {list(Model._fields.keys())}")
