import psycopg2

def check_children(parent_id):
    conn = psycopg2.connect(dbname="Odoo", user="odoo", password="odoo", host="localhost")
    cur = conn.cursor()
    
    print(f"Children of ID {parent_id}:")
    cur.execute("SELECT id, name, parent_id, sequence FROM account_financial_report WHERE parent_id = %s ORDER BY sequence", (parent_id,))
    rows = cur.fetchall()
    
    for r in rows:
        print(f"ID: {r[0]} | Name: {r[1]} | Sequence: {r[3]}")
            
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_children(5) # Assets
    print("-" * 20)
    check_children(6) # Liability (top)
    print("-" * 20)
    check_children(7) # Liability (sub)
