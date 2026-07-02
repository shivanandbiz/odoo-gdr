
import xmlrpc.client

url = 'http://localhost:8069'
db = 'Odoo'
username = 'admin'
password = 'admin123' # from odoo.conf

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

# Search for frontend assets
asset_ids = models.execute_kw(db, uid, password, 'ir.attachment', 'search', [[
    ('url', 'like', '/web/assets/%'),
    ('url', 'like', '%frontend%')
]])

print(f"Found {len(asset_ids)} frontend asset attachments")

if asset_ids:
    print(f"Deleting asset attachments: {asset_ids}")
    models.execute_kw(db, uid, password, 'ir.attachment', 'unlink', [asset_ids])
    print("Deleted.")
else:
    print("No attachments found to delete.")
