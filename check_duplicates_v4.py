
from collections import defaultdict

# 1. Check product.product
print("=== Checking product.product duplicates ===")
variants = env['product.product'].search([])
print(f"Total variants: {len(variants)}")

v_code_map = defaultdict(list)
v_name_map = defaultdict(list)
v_barcode_map = defaultdict(list)

for v in variants:
    if v.default_code:
        v_code_map[v.default_code.strip().lower()].append(v)
    if v.name:
        v_name_map[v.name.strip().lower()].append(v)
    if v.barcode:
        v_barcode_map[v.barcode.strip().lower()].append(v)

print(f"Duplicate codes: {len([c for c, rs in v_code_map.items() if len(rs) > 1])}")
print(f"Duplicate names: {len([n for n, rs in v_name_map.items() if len(rs) > 1])}")
print(f"Duplicate barcodes: {len([b for b, rs in v_barcode_map.items() if len(rs) > 1])}")

# 2. Check for "Duplicate" in name
print("\n=== Checking for 'Duplicate' keyword in names ===")
dupes_keyword = env['product.template'].search([('name', 'ilike', 'duplicate')])
print(f"Products with 'duplicate' in name: {len(dupes_keyword)}")
for p in dupes_keyword[:10]:
    print(f"  [{p.id}] {p.name}")

# 3. Check for exact same name AND category
print("\n=== Checking for same name AND category ===")
name_cat_map = defaultdict(list)
for p in env['product.template'].search([]):
    key = (p.name.strip().lower(), p.categ_id.id)
    name_cat_map[key].append(p)

duplicate_name_cat = {k: rs for k, rs in name_cat_map.items() if len(rs) > 1}
print(f"Found {len(duplicate_name_cat)} Name+Category matches.")
