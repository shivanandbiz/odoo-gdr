import psycopg2
import json

def sql_reformat():
    conn = psycopg2.connect(dbname="Odoo", user="odoo", password="odoo", host="localhost")
    cur = conn.cursor()
    
    # 1. Clean up existing sub-lines for Assets (5) and Liabilities (6)
    # We want a fresh start for children of 5 and 6
    cur.execute("DELETE FROM account_account_financial_report_type WHERE report_id IN (SELECT id FROM account_financial_report WHERE parent_id IN (5, 6, 7))")
    cur.execute("DELETE FROM account_financial_report WHERE parent_id IN (5, 6, 7)")
    
    # 2. Update Assets and Liabilities top lines
    cur.execute("UPDATE account_financial_report SET name = %s, type = 'sum', style_overwrite = '2' WHERE id = 5", (json.dumps({'en_US': 'ASSETS'}),))
    cur.execute("UPDATE account_financial_report SET name = %s, type = 'sum', style_overwrite = '2' WHERE id = 6", (json.dumps({'en_US': 'LIABILITIES'}),))
    
    # 3. Create EQUITY section as child of Balance Sheet (4)
    # Check if EQUITY exists first
    cur.execute("SELECT id FROM account_financial_report WHERE name::text ILIKE '%EQUITY%'")
    equity_row = cur.fetchone()
    if equity_row:
        equity_id = equity_row[0]
        cur.execute("UPDATE account_financial_report SET parent_id = 4, sequence = 30, style_overwrite = '2' WHERE id = %s", (equity_id,))
    else:
        cur.execute("INSERT INTO account_financial_report (name, parent_id, type, sequence, display_detail, style_overwrite, sign) VALUES (%s, 4, 'sum', 30, 'detail_flat', '2', '1') RETURNING id", (json.dumps({'en_US': 'EQUITY'}),))
        equity_id = cur.fetchone()[0]

    # --- ASSETS (5) ---
    # Current Assets Group
    cur.execute("INSERT INTO account_financial_report (name, parent_id, type, sequence, display_detail, style_overwrite, sign) VALUES (%s, 5, 'sum', 10, 'detail_flat', '2', '1') RETURNING id", (json.dumps({'en_US': 'Current Assets'}),))
    curr_assets_id = cur.fetchone()[0]
    
    def add_line(name, parent, types, seq):
        cur.execute("INSERT INTO account_financial_report (name, parent_id, type, sequence, display_detail, style_overwrite, sign) VALUES (%s, %s, 'account_type', %s, 'detail_with_hierarchy', '0', '1') RETURNING id", (json.dumps({'en_US': name}), parent, seq))
        line_id = cur.fetchone()[0]
        for t in types:
            cur.execute("INSERT INTO account_account_financial_report_type (report_id, account_type_id) VALUES (%s, %s)", (line_id, t))

    add_line('Bank and Cash Accounts', curr_assets_id, [3], 10)
    add_line('Receivables', curr_assets_id, [1], 20)
    add_line('Current Assets', curr_assets_id, [5], 30)
    add_line('Prepayments', curr_assets_id, [7], 40)
    
    add_line('Plus Fixed Assets', 5, [8], 20)
    add_line('Plus Non-current Assets', 5, [6], 30)

    # --- LIABILITIES (6) ---
    cur.execute("INSERT INTO account_financial_report (name, parent_id, type, sequence, display_detail, style_overwrite, sign) VALUES (%s, 6, 'sum', 10, 'detail_flat', '2', '1') RETURNING id", (json.dumps({'en_US': 'Current Liabilities'}),))
    curr_liab_id = cur.fetchone()[0]
    
    add_line('Current Liabilities', curr_liab_id, [9], 10)
    add_line('Payables', curr_liab_id, [2], 20)
    
    add_line('Plus Non-current Liabilities', 6, [10], 20)
    
    # --- EQUITY ---
    add_line('Unallocated Earnings', equity_id, [11, 12], 10)
    
    # Handle Profit/Loss (8)
    cur.execute("UPDATE account_financial_report SET parent_id = %s, sequence = 20, name = %s WHERE id = 8", (equity_id, json.dumps({'en_US': 'Profit (Loss) for the period'})))

    conn.commit()
    cur.close()
    conn.close()
    print("Balance Sheet reformatted successfully via SQL.")

if __name__ == "__main__":
    sql_reformat()
