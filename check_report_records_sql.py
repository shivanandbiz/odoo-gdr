import psycopg2

def check_records():
    conn = psycopg2.connect(dbname="Odoo", user="odoo", password="odoo", host="localhost")
    cur = conn.cursor()
    
    print("RECORDS in account_financial_report:")
    cur.execute("SELECT id, name, parent_id, sequence FROM account_financial_report ORDER BY sequence")
    rows = cur.fetchall()
    
    # Map ID to Name for easier reading
    id_map = {r[0]: r[1] for r in rows}
    
    for r in rows:
        parent_name = id_map.get(r[2], "None") if r[2] else "None"
        print(f"ID: {r[0]} | Name: {r[1]} | Parent: {parent_name} | Sequence: {r[3]}")
            
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_records()
