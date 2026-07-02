import psycopg2

def check_types():
    conn = psycopg2.connect(dbname="Odoo", user="odoo", password="odoo", host="localhost")
    cur = conn.cursor()
    
    cur.execute("SELECT id, name FROM account_account_type")
    rows = cur.fetchall()
    for r in rows:
        print(f"ID: {r[0]} | Name: {r[1]}")
            
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_types()
