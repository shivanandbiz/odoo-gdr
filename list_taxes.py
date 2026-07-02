# list_taxes.py
taxes = env['account.tax'].search([('type_tax_use', '=', 'sale')])
for t in taxes:
    print(f"Tax: '{t.name}' | Amount: {t.amount} | Type: {t.type_tax_use}")
