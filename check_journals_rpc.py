import sys
import xmlrpc.client

url = 'http://localhost:8069'
db = 'shivodoo_db'
username = 'admin'
password = '1'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})

if not uid:
    print("Authentication failed")
    sys.exit(1)

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

journals = models.execute_kw(db, uid, password,
    'account.journal', 'search_read',
    [[['type', 'in', ['bank', 'cash']]]],
    {'fields': ['name', 'type', 'company_id']})

print("Bank/Cash Journals:", journals)
