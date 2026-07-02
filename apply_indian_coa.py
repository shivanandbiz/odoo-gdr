import odoo
from odoo import api, SUPERUSER_ID

# Find Indian chart template
template = env['account.chart.template'].search([('name', '=', 'Indian Tax and Accounting Template')], limit=1)
if not template:
    template = env['account.chart.template'].search([('name', 'ilike', 'India')], limit=1)

if template:
    print(f"Applying Chart Template: {template.name} (ID: {template.id})")
    # In Odoo 17+, you set the chart_template field on the company
    env.company.chart_template = template.id
    # Odoo usually triggers the installation automatically or you might need to force it
    # But often just setting the field works or we can call the installation method if it exists
    env.cr.commit()
    print("Chart template updated. Odoo should now be loading the Indian taxes.")
else:
    print("Indian Chart Template not found!")
