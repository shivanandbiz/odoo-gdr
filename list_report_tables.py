import psycopg2

def list_rel_tables():
    conn = psycopg2.connect(dbname="Odoo", user="odoo", password="odoo", host="localhost")
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'account_financial_report%'")
    rows = cur.fetchall()
    for r in rows:
        print(f"Table: {r[0]}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    list_rel_tables()
