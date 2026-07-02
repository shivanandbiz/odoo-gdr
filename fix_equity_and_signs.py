import psycopg2
import json

def fix_equity():
    conn = psycopg2.connect(dbname="Odoo", user="odoo", password="odoo", host="localhost")
    cur = conn.cursor()
    
    # Find Equity ID
    cur.execute("SELECT id FROM account_financial_report WHERE name::text ILIKE '%EQUITY%' AND parent_id = 4")
    row = cur.fetchone()
    if not row:
        print("EQUITY line not found.")
        return
    equity_id = row[0]
    
    # Re-create Profit (Loss) for the period line (type account_report)
    # Linked to P&L report (ID 1)
    cur.execute("INSERT INTO account_financial_report (name, parent_id, type, sequence, display_detail, style_overwrite, sign, account_report_id) VALUES (%s, %s, 'account_report', 20, 'no_detail', '0', '-1', 1)", (json.dumps({'en_US': 'Profit (Loss) for the period'}), equity_id))
    
    # Fix the sign for Liabilities and Equity
    # In Odoo reports, if it's a credit balance and we want it positive, sign should be -1
    cur.execute("UPDATE account_financial_report SET sign = '-1' WHERE id = 6") # LIABILITIES
    cur.execute("UPDATE account_financial_report SET sign = '-1' WHERE id = %s", (equity_id,)) # EQUITY
    
    # Fix signs for children of LIABILITIES and EQUITY
    cur.execute("UPDATE account_financial_report SET sign = '-1' WHERE parent_id IN (6, %s)", (equity_id,))
    
    conn.commit()
    cur.close()
    conn.close()
    print("Equity fixed and signs updated.")

if __name__ == "__main__":
    fix_equity()
