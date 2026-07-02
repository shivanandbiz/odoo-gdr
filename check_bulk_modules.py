import xmlrpc.client

url = 'http://localhost:8069'
db = 'shivodoo_db'
username = 'admin'
password = 'admin_password' # Wait, do I have the password? I can just use odoo shell or direct DB access

# direct DB access
import psycopg2
conn = psycopg2.connect(dbname="shivodoo_db", user="biz")
cur = conn.cursor()
cur.execute("SELECT name, state FROM ir_module_module WHERE name IN ('multi_bill_payment', 'gdr_bulk_payments')")
for row in cur.fetchall():
    print(row)
