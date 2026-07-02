import odoo
from odoo import api, SUPERUSER_ID

company = env.company
print(f"Company: {company.name}")
print(f"Country: {company.country_id.name} ({company.country_id.code})")
print(f"Chart Template: {company.chart_template}")

# Check if taxes are loaded
tax_count = env['account.tax'].search_count([('company_id', '=', company.id)])
print(f"Tax Count: {tax_count}")
