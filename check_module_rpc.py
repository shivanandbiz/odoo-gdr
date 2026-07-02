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

# Check if the module is installed
module = models.execute_kw(db, uid, password,
    'ir.module.module', 'search_read',
    [[['name', '=', 'account_india_credit_debit_bridge']]],
    {'fields': ['name', 'state']})

print("Module status:", module)

# Check if l10n_in_gst_reason is in account.debit.note
fields = models.execute_kw(db, uid, password,
    'account.debit.note', 'fields_get',
    [],
    {'attributes': ['string', 'type']})

print("l10n_in_gst_reason in fields:", 'l10n_in_gst_reason' in fields)
