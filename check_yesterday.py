
yesterday = '2026-04-20'
new_products = env['product.template'].search([('create_date', '>=', yesterday)])
print(f"Products created on or after {yesterday}: {len(new_products)}")
for p in new_products[:20]:
    print(f"  [{p.id}] {p.name} (Code: {p.default_code})")
