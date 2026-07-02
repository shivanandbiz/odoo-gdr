
from collections import Counter

# Search for exact description duplicates (non-empty)
descs = [p.description for p in env['product.template'].search([('description', '!=', False)])]
counts = Counter(descs)
dupes = {d: c for d, c in counts.items() if c > 1}

print(f"Exact description duplicates: {len(dupes)}")
for d, c in list(dupes.items())[:5]:
    print(f"  '{d[:50]}...': {c} records")
