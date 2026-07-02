# list_all_taxes.py
taxes = env['account.tax'].search([])
for t in taxes:
    print(f"Tax: '{t.name}' | Amount: {t.amount} | Type: {t.type_tax_use}")
