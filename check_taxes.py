taxes = env['account.tax'].search([])
for t in taxes:
    print(f"ID: {t.id}, Name: {t.name}, Type: {t.type_tax_use}, Amount: {t.amount}")
