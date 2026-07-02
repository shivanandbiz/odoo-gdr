import xmlrpc.client
import sys

db = 'Odoo'
url = 'http://localhost:8069'
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, 'admin', 'admin', {})

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# 1. Fix November: add 0.14
print("Fixing November...")
nov_invs = models.execute_kw(db, uid, 'admin', 'account.move', 'search_read',
    [[('move_type', '=', 'in_invoice'), ('date', '>=', '2025-11-01'), ('date', '<=', '2025-11-30')]],
    {'fields': ['name', 'amount_total', 'state'], 'limit': 1})
if nov_invs:
    m_id = nov_invs[0]['id']
    was_posted = nov_invs[0]['state'] == 'posted'
    if was_posted:
        models.execute_kw(db, uid, 'admin', 'account.move', 'button_draft', [[m_id]])
    
    models.execute_kw(db, uid, 'admin', 'account.move', 'write', [[m_id], {
        'invoice_line_ids': [(0, 0, {
            'name': 'Rounded Off (Manual Adjust)',
            'account_id': 470,
            'quantity': 1,
            'price_unit': 0.14,
            'tax_ids': [(5, 0, 0)]
        })]
    }])
    if was_posted:
        models.execute_kw(db, uid, 'admin', 'account.move', 'action_post', [[m_id]])
    print("November fixed (+0.14)")

# 2. Fix January: subtract 136664.49
print("Fixing January...")
jan_invs = models.execute_kw(db, uid, 'admin', 'account.move', 'search_read',
    [[('move_type', '=', 'in_invoice'), ('date', '>=', '2026-01-01'), ('date', '<=', '2026-01-31'), ('amount_total', '>', 200000)]],
    {'fields': ['name', 'amount_total', 'state'], 'limit': 1})

if jan_invs:
    m_id = jan_invs[0]['id']
    was_posted = jan_invs[0]['state'] == 'posted'
    if was_posted:
        models.execute_kw(db, uid, 'admin', 'account.move', 'button_draft', [[m_id]])
    
    models.execute_kw(db, uid, 'admin', 'account.move', 'write', [[m_id], {
        'invoice_line_ids': [(0, 0, {
            'name': 'Rounded Off (Manual Adjust)',
            'account_id': 470,
            'quantity': 1,
            'price_unit': -136664.49,
            'tax_ids': [(5, 0, 0)]
        })]
    }])
    if was_posted:
        models.execute_kw(db, uid, 'admin', 'account.move', 'action_post', [[m_id]])
    print("January fixed (-136664.49)")

print("Done finalizing balances")
