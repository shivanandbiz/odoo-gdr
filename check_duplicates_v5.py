
from collections import defaultdict

# Search including ARCHIVED products
all_products = env['product.template'].with_context(active_test=False).search([])
print(f"Total products (including archived): {len(all_products)}")

name_map = defaultdict(list)
code_map = defaultdict(list)

for p in all_products:
    n = (p.name or "").strip().lower()
    c = (p.default_code or "").strip().lower()
    if n:
        name_map[n].append(p)
    if c:
        code_map[c].append(p)

dupe_names = {n: rs for n, rs in name_map.items() if len(rs) > 1}
dupe_codes = {c: rs for c, rs in code_map.items() if len(rs) > 1}

print(f"Duplicate names (incl archived): {len(dupe_names)}")
print(f"Duplicate codes (incl archived): {len(dupe_codes)}")

if dupe_names:
    for n, rs in list(dupe_names.items())[:10]:
        print(f"  Name '{n}': {[r.id for r in rs]} (Active: {[r.active for r in rs]})")
