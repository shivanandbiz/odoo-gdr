import odoo
from odoo import api, SUPERUSER_ID

company = env.company
clashing_codes = ['101300', '201000', '201100', '211000', '211100']
for code in clashing_codes:
    acc = env['account.account'].search([('code', '=', code), ('company_ids', 'in', [company.id])], limit=1)
    if acc:
        new_code = f"999.{code}"
        print(f"Renaming {code} to {new_code}")
        acc.code = new_code

env.cr.commit()
print("Renaming complete.")
