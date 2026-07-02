import xmlrpc.client
import sys

db = 'Odoo'
user = 'admin'  # Let's check admin username
password = 'admin_password'

url = 'http://localhost:8069'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, 'admin', 'admin', {})

if not uid:
    print("Authentication failed")
    sys.exit()

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

# Get all purchase journal entries or just purchase invoices
# In Odoo, Account Move with move_type='in_invoice' or 'in_refund'
# And state='posted'

invoices = models.execute_kw(db, uid, 'admin', 'account.move', 'search_read',
    [[('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]],
    {'fields': ['date', 'amount_total', 'amount_untaxed', 'state']})

from collections import defaultdict
import datetime

monthly_totals = defaultdict(float)

for inv in invoices:
    date = datetime.datetime.strptime(inv['date'], '%Y-%m-%d')
    month = date.strftime('%Y-%m')
    monthly_totals[month] += inv['amount_total']

for m in sorted(monthly_totals.keys()):
    print(f"{m}: {monthly_totals[m]:.2f}")

print(f"Total: {sum(monthly_totals.values()):.2f}")
