
from collections import defaultdict

# Grouping by name and code to find duplicates
templates = env['product.template'].with_context(active_test=False).search([])
print(f"Total templates: {len(templates)}")

name_map = defaultdict(list)
code_map = defaultdict(list)

for t in templates:
    n = (t.name or "").strip().lower()
    c = (t.default_code or "").strip().lower()
    if n: name_map[n].append(t)
    if c: code_map[c].append(t)

print(f"Name groups with >1 record: {len([n for n, rs in name_map.items() if len(rs) > 1])}")
print(f"Code groups with >1 record: {len([c for c, rs in code_map.items() if len(rs) > 1])}")

# Let's check if there are products with the same FIRST 20 characters of the name
print("\n--- Similarity check (First 20 chars) ---")
short_name_map = defaultdict(list)
for t in templates:
    n = (t.name or "").strip().lower()[:20]
    if n: short_name_map[n].append(t)

similar = {n: rs for n, rs in short_name_map.items() if len(rs) > 1}
print(f"Found {len(similar)} groups with similar names.")
for n, rs in list(similar.items())[:10]:
    print(f"  '{n}...': {len(rs)} records")
