
from collections import defaultdict

# Check Partners
partners = env['res.partner'].search([])
print(f"Total partners: {len(partners)}")

p_name_map = defaultdict(list)
p_vat_map = defaultdict(list)

for p in partners:
    n = (p.name or "").strip().lower()
    v = (p.vat or "").strip().lower()
    if n:
        p_name_map[n].append(p)
    if v:
        p_vat_map[v].append(p)

dupe_p_names = {n: rs for n, rs in p_name_map.items() if len(rs) > 1}
dupe_p_vat = {v: rs for v, rs in p_vat_map.items() if len(rs) > 1}

print(f"Duplicate partner names: {len(dupe_p_names)}")
print(f"Duplicate partner VATs: {len(dupe_p_vat)}")

if dupe_p_names:
    print("\nSample duplicate partner names:")
    for n, rs in list(dupe_p_names.items())[:5]:
        print(f"  '{n}': {[r.id for r in rs]}")
