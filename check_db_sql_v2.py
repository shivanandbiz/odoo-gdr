import psycopg2
import json

def check_sql():
    try:
        conn = psycopg2.connect(dbname="Odoo", user="odoo", password="odoo", host="localhost")
        cur = conn.cursor()
        
        print("Checking account_report_line table:")
        # Casting jsonb to text for searching
        cur.execute("SELECT id, name, parent_id FROM account_report_line WHERE name::text ILIKE '%Bank and Cash Accounts%' OR name::text ILIKE '%ASSETS%'")
        rows = cur.fetchall()
        for r in rows:
            print(f"  Line: {r}")
            
        print("\nChecking all account_report names:")
        cur.execute("SELECT id, name FROM account_report")
        rows = cur.fetchall()
        for r in rows:
            print(f"  Report: {r}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_sql()
