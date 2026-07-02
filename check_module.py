import psycopg2

conn = psycopg2.connect("dbname=shivodoo_db user=biz")
cur = conn.cursor()
cur.execute("SELECT state FROM ir_module_module WHERE name = 'account_india_credit_debit_bridge'")
res = cur.fetchone()
print(f"Module state: {res[0] if res else 'Not found'}")
conn.close()
