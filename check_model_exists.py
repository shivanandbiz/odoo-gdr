import psycopg2

def check_model_exists():
    conn = psycopg2.connect(dbname="Odoo", user="odoo", password="odoo", host="localhost")
    cur = conn.cursor()
    cur.execute("SELECT id, model FROM ir_model WHERE model = 'account.financial.report'")
    row = cur.fetchone()
    if row:
        print(f"Model found: {row}")
    else:
        print("Model NOT found in ir_model.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_model_exists()
