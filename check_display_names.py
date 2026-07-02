
from collections import Counter

# Search for exact display_name duplicates
names = [p.display_name for p in env['product.template'].search([])]
counts = Counter(names)
dupes = {n: c for n, c in counts.items() if c > 1}

print(f"Exact display_name duplicates: {len(dupes)}")
for n, c in list(dupes.items())[:10]:
    print(f"  '{n}': {c} records")
