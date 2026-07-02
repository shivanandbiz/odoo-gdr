
import psycopg2

conn = psycopg2.connect(dbname='Odoo', user='odoo', password='odoo', host='localhost')
cur = conn.cursor()

print("--- product_template (SQL) ---")
cur.execute("SELECT name, count(*) FROM product_template GROUP BY name HAVING count(*) > 1")
res = cur.fetchall()
print(f"Found {len(res)} duplicate names in SQL.")

print("\n--- product_product (SQL) ---")
cur.execute("SELECT default_code, count(*) FROM product_product WHERE default_code IS NOT NULL GROUP BY default_code HAVING count(*) > 1")
res = cur.fetchall()
print(f"Found {len(res)} duplicate codes in SQL.")

cur.close()
conn.close()
