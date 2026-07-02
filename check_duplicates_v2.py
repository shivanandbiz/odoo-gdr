
# Search for products with similar names (ignoring case and whitespace)
print("=== Checking duplicates by Name (normalized) ===")
query = """
    SELECT LOWER(TRIM(name)), count(*)
    FROM product_template
    GROUP BY LOWER(TRIM(name))
    HAVING count(*) > 1
"""
env.cr.execute(query)
res = env.cr.fetchall()
print(f"Found {len(res)} Normalized Names with duplicates.")
for name, count in res[:20]:
    print(f"  '{name}': {count} records")

# Search for products with similar Internal References
print("\n=== Checking duplicates by Internal Reference (normalized) ===")
query = """
    SELECT LOWER(TRIM(default_code)), count(*)
    FROM product_template
    WHERE default_code IS NOT NULL AND default_code != ''
    GROUP BY LOWER(TRIM(default_code))
    HAVING count(*) > 1
"""
env.cr.execute(query)
res = env.cr.fetchall()
print(f"Found {len(res)} Normalized Internal References with duplicates.")
for code, count in res[:20]:
    print(f"  '{code}': {count} records")

# Total count
print(f"\nTotal product templates: {env['product.template'].search_count([])}")
print(f"Total product variants: {env['product.product'].search_count([])}")
