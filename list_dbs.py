
import psycopg2

try:
    conn = psycopg2.connect(
        dbname='postgres',
        user='odoo',
        password='odoo',
        host='localhost'
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
    dbs = cur.fetchall()
    print("Databases found:")
    for db in dbs:
        print(f"  - {db[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
