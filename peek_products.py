
products = env['product.template'].search([], limit=100)
for p in products:
    print(f"[{p.id}] Code: {p.default_code} | Name: {p.name}")
