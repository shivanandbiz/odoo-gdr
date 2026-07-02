
from datetime import datetime, timedelta

today = datetime.now().date()
new_products = env['product.template'].search([('create_date', '>=', today.strftime('%Y-%m-%d'))])
print(f"Products created today: {len(new_products)}")
for p in new_products[:20]:
    print(f"  [{p.id}] {p.name} (Code: {p.default_code})")
