
from collections import defaultdict

# 1. Deduplicate by Internal Reference
print("=== Checking duplicates by Internal Reference (ORM) ===")
products = env['product.template'].search([('default_code', '!=', False)])
code_map = defaultdict(list)
for p in products:
    code_map[p.default_code.strip().lower()].append(p)

duplicate_codes = {code: recs for code, recs in code_map.items() if len(recs) > 1}
print(f"Found {len(duplicate_codes)} Internal References with duplicates.")

# 2. Deduplicate by Name
print("\n=== Checking duplicates by Name (ORM) ===")
# Search for all products
all_products = env['product.template'].search([])
name_map = defaultdict(list)
for p in all_products:
    name_map[p.name.strip().lower()].append(p)

duplicate_names = {name: recs for name, recs in name_map.items() if len(recs) > 1}
print(f"Found {len(duplicate_names)} Names with duplicates.")

# Print some samples
if duplicate_names:
    print("\nSample duplicate names:")
    for name, recs in list(duplicate_names.items())[:10]:
        print(f"  '{name}': {len(recs)} records (IDs: {[r.id for r in recs]})")

print(f"\nTotal product templates: {len(all_products)}")
