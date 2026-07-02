
from collections import Counter

# Search for exact code duplicates in product.product (incl archived)
codes = [v.default_code for v in env['product.product'].with_context(active_test=False).search([('default_code', '!=', False)])]
counts = Counter(codes)
dupes = {c: count for c, count in counts.items() if count > 1}

print(f"Exact variant code duplicates (incl archived): {len(dupes)}")
for c, count in list(dupes.items())[:10]:
    print(f"  '{c}': {count} records")
