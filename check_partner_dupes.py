
from collections import defaultdict

# Check by Name (normalized)
name_map = defaultdict(list)
for p in env['res.partner'].search([('active', '=', True)]):
    name_map[p.name.strip().lower()].append(p)

dupes = {name: recs for name, recs in name_map.items() if len(recs) > 1}

print(f"=== Active Duplicate Partners (Name) ===")
if not dupes:
    print("Zero duplicates found.")
else:
    for name, recs in dupes.items():
        print(f"'{name}': {len(recs)} records")
        for r in recs:
            print(f"  [{r.id}] VAT: {r.vat} | Email: {r.email}")

# Check by VAT
vat_map = defaultdict(list)
for p in env['res.partner'].search([('vat', '!=', False), ('active', '=', True)]):
    vat_map[p.vat.strip().upper()].append(p)

vat_dupes = {v: recs for v, recs in vat_map.items() if len(recs) > 1}
print(f"\n=== Active Duplicate Partners (VAT) ===")
if not vat_dupes:
    print("Zero duplicates found.")
else:
    for v, recs in vat_dupes.items():
        print(f"'{v}': {len(recs)} records")
