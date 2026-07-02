import odoo
from odoo import api, SUPERUSER_ID

Model = env['res.company']
rel_fields = [f for f in Model._fields.keys() if 'chart' in f or 'localization' in f or 'l10n' in f]
print(f"Company localization fields: {rel_fields}")

# Show current values for the company
company = env.company
for f in rel_fields:
    try:
        val = getattr(company, f)
        print(f"{f}: {val}")
    except:
        pass
