import xmlrpc.client
db = 'Odoo'
url = 'http://localhost:8069'
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, 'admin', 'admin', {})
m = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)

reports = m.execute_kw(db, uid, 'admin', 'account.financial.report', 'search_read', [[]], {'fields': ['name']})
print("Total reports:", len(reports))
for r in reports:
    print(r)
