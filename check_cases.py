
from collections import defaultdict

name_map = defaultdict(list)
for p in env['product.template'].search([]):
    name_map[p.name.strip().lower()].append(p)

for name, recs in name_map.items():
    if len(recs) > 1:
        print(f"Name group: '{name}'")
        for r in recs:
            print(f"  [{r.id}] Name: '{r.name}' | Code: {r.default_code}")
