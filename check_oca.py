import psycopg2

conn = psycopg2.connect("dbname='shivodoo_db' user='biz' password='password'")
cur = conn.cursor()

cur.execute("SELECT name, state FROM ir_module_module WHERE name LIKE 'account_statement_import%' OR name LIKE 'account_reconcile%';")
rows = cur.fetchall()

for row in rows:
    print(f"Module: {row[0]}, State: {row[1]}")

cur.close()
conn.close()
