import psycopg2
conn = psycopg2.connect(dbname='Odoo', user='odoo', password='odoo', host='localhost')
cur = conn.cursor()
cur.execute("SELECT count(*) FROM account_move WHERE date >= '2025-04-01' AND date <= '2026-03-31'")
print('Total moves:', cur.fetchone()[0])
cur.execute("SELECT state, count(*) FROM account_move WHERE date >= '2025-04-01' AND date <= '2026-03-31' GROUP BY state")
print('Moves by state:', cur.fetchall())
