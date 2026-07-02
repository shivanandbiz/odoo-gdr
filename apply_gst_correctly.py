import odoo
from odoo import api, SUPERUSER_ID

# For India, the template code is 'in'
template_code = 'in'
company = env.company

print(f"Applying Chart Template '{template_code}' to company '{company.name}'...")

try:
    # try_loading will load the chart of accounts, taxes, etc.
    # In Odoo 17, try_loading is a method on account.chart.template
    env['account.chart.template'].try_loading(template_code, company)
    env.cr.commit()
    print("Chart template loaded successfully!")
    
    # Verify taxes now
    tax_count = env['account.tax'].search_count([('company_id', '=', company.id)])
    print(f"New Tax Count: {tax_count}")
    
    # Check if a GST tax exists
    gst_tax = env['account.tax'].search([('name', 'ilike', 'GST'), ('company_id', '=', company.id)], limit=1)
    if gst_tax:
        print(f"Found GST Tax: {gst_tax.name}")
    else:
        print("GST Tax not found. Checking all taxes...")
        all_taxes = env['account.tax'].search([('company_id', '=', company.id)], limit=5)
        for t in all_taxes:
            print(f" - {t.name}")

except Exception as e:
    print(f"Error loading template: {e}")
