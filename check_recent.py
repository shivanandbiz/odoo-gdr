
products = env['product.template'].search([], order='id desc', limit=20)
for p in products:
    print(f"[{p.id}] {p.name} (Created: {p.create_date})")
