import xmlrpc.client
import sys

db = 'Odoo'
url = 'http://localhost:8069'
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, 'admin', 'admin', {})

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

# Fetch move lines for a specific invoice
moves = models.execute_kw(db, uid, 'admin', 'account.move', 'search_read',
    [[('ref', 'like', '12/25-26%'), ('partner_id.name', 'ilike', 'Laxmi Hardware')]],
    {'fields': ['name', 'ref', 'partner_id', 'amount_total', 'invoice_line_ids', 'state']})

if not moves:
    print("Move not found")
    sys.exit()

move = moves[0]
print(f"Move: {move['name']} Ref: {move['ref']} Amount: {move['amount_total']} State: {move['state']}")

lines = models.execute_kw(db, uid, 'admin', 'account.move.line', 'read',
    [move['invoice_line_ids']],
    {'fields': ['name', 'account_id', 'price_unit', 'price_subtotal', 'price_total', 'tax_ids']})

for idx, l in enumerate(lines):
    print(f"[{idx}] {l['name']} - Acc: {l['account_id'][1]} - Unit: {l['price_unit']} - Sub: {l['price_subtotal']} - Tot: {l['price_total']} - Taxes: {l['tax_ids']}")

