import odoo
from odoo import api, SUPERUSER_ID

Model = env['account.chart.template']
print(f"Fields on {Model._name}: {list(Model._fields.keys())}")

# Try to find templates
templates = Model.search([], limit=10)
for t in templates:
    # Try common fields to identify it
    display_name = getattr(t, 'display_name', 'N/A')
    country = getattr(t, 'country_id', 'N/A')
    print(f"ID: {t.id} | Display Name: {display_name} | Country: {country}")
