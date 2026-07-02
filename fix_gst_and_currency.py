
# Fix Script: Currency and Taxes
print("--- FIXING CURRENCY ---")
inr = env['res.currency'].with_context(active_test=False).search([('name', '=', 'INR')], limit=1)
if inr:

    inr.active = True
    env.company.currency_id = inr.id
    print(f"Company currency set to INR ({inr.id})")
else:
    print("INR Currency not found!")

print("\n--- FIXING TAXES ---")
# Try to find Indian GST 18
tax_18 = env['account.tax'].search([('amount', '=', 18), ('type_tax_use', '=', 'sale'), ('company_id', '=', env.company.id)], limit=1)
if not tax_18:
    print("Creating GST 18% (Sale)...")
    tax_18 = env['account.tax'].create({
        'name': 'GST 18%',
        'amount': 18,
        'type_tax_use': 'sale',
        'company_id': env.company.id,
    })

tax_18_p = env['account.tax'].search([('amount', '=', 18), ('type_tax_use', '=', 'purchase'), ('company_id', '=', env.company.id)], limit=1)
if not tax_18_p:
    print("Creating GST 18% (Purchase)...")
    tax_18_p = env['account.tax'].create({
        'name': 'GST 18%',
        'amount': 18,
        'type_tax_use': 'purchase',
        'company_id': env.company.id,
    })

print(f"Using Tax: {tax_18.name} (Sale) and {tax_18_p.name} (Purchase)")

print("\n--- UPDATING PRODUCTS ---")
products = env['product.template'].search([])
count = 0
for p in products:
    # Update taxes
    p.write({
        'taxes_id': [(6, 0, [tax_18.id])],
        'supplier_taxes_id': [(6, 0, [tax_18_p.id])]
    })
    count += 1
    if count % 500 == 0:
        env.cr.commit()
        print(f"Updated {count} products...")

env.cr.commit()
print(f"Finished. Updated {count} products to GST 18% and INR currency.")
