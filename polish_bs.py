import psycopg2
import json

def final_polish():
    conn = psycopg2.connect(dbname="Odoo", user="odoo", password="odoo", host="localhost")
    cur = conn.cursor()
    
    # Set top sequences
    cur.execute("UPDATE account_financial_report SET sequence = 10, name = %s, style_overwrite = '2' WHERE id = 5", (json.dumps({'en_US': 'ASSETS'}),))
    cur.execute("UPDATE account_financial_report SET sequence = 20, name = %s, style_overwrite = '2' WHERE id = 6", (json.dumps({'en_US': 'LIABILITIES'}),))
    
    # Find Equity ID again to be sure
    cur.execute("SELECT id FROM account_financial_report WHERE name::text ILIKE '%EQUITY%' AND parent_id = 4")
    row = cur.fetchone()
    if row:
        equity_id = row[0]
        cur.execute("UPDATE account_financial_report SET sequence = 30, style_overwrite = '2' WHERE id = %s", (equity_id,))

    conn.commit()
    cur.close()
    conn.close()
    print("Balance Sheet final polish applied.")

if __name__ == "__main__":
    final_polish()
