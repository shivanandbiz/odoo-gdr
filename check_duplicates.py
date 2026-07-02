
# Group by Internal Reference (default_code)
print("=== Checking duplicates by Internal Reference ===")
query = """
    SELECT default_code, count(*)
    FROM product_template
    WHERE default_code IS NOT NULL AND default_code != ''
    GROUP BY default_code
    HAVING count(*) > 1
"""
env.cr.execute(query)
res = env.cr.fetchall()
print(f"Found {len(res)} Internal References with duplicates.")
for code, count in res[:10]:
    print(f"  {code}: {count} records")

# Group by Name
print("\n=== Checking duplicates by Name ===")
query = """
    SELECT name, count(*)
    FROM product_template
    GROUP BY name
    HAVING count(*) > 1
"""
env.cr.execute(query)
res = env.cr.fetchall()
print(f"Found {len(res)} Names with duplicates.")
for name, count in res[:10]:
    print(f"  {name}: {count} records")
