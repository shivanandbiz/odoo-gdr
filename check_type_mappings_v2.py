import psycopg2

def check_types():
    conn = psycopg2.connect(dbname="Odoo", user="odoo", password="odoo", host="localhost")
    cur = conn.cursor()
    
    print("MAPPINGS in account_account_financial_report_type:")
    cur.execute("SELECT report_id, account_type_id FROM account_account_financial_report_type")
    rows = cur.fetchall()
    for r in rows:
        print(f"  Report Line ID: {r[0]} | Account Type ID: {r[1]}")
            
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_types()
