
from collections import defaultdict

desc_map = defaultdict(list)
for p in env['product.template'].search([('description', '!=', False)]):
    desc_map[p.description].append(p)

for desc, recs in desc_map.items():
    if len(recs) > 1:
        print(f"\nDescription: {desc}")
        for r in recs:
            print(f"  [{r.id}] Name: {r.name} | Code: {r.default_code}")
