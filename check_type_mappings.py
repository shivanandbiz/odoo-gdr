import psycopg2

def check_account_types():
    conn = psycopg2.connect(dbname="Odoo", user="odoo", password="odoo", host="localhost")
    cur = conn.cursor()
    
    # In Odoo 17+, account types are just a selection on account.account,
    # but some modules might still use account.account.type or similar.
    # However, OdooMates accounting_pdf_reports might have its own mapping.
    
    # Let's check the mapping table for account.financial.report and account types.
    # The table name is usually account_financial_report_account_type_rel
    try:
        cur.execute("SELECT * FROM account_financial_report_account_type_rel")
        rows = cur.fetchall()
        print("Mappings (Report Line ID, Account Type ID):")
        for r in rows:
            print(f"  {r}")
    except:
        print("Table account_financial_report_account_type_rel not found.")
        conn.rollback()
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_account_types()
