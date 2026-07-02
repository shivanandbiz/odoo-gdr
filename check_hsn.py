import xmlrpc.client
import json

url = 'https://biztechnosys1.odoo.com'
db = 'biztechnosys1'
username = 'shivanand.b@biztechnosys.com'
password = 'Shivu@2467'

try:
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, username, password, {})
        
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    fields = models.execute_kw(db, uid, password, 'ir.model.fields', 'search_read', 
        [[['name', '=', 'l10n_in_is_gst_registered'], ['model', '=', 'res.company']]], 
        {'fields': ['name', 'compute', 'depends']})
    print("\nField def:", json.dumps(fields, indent=2))

except Exception as e:
    print(f"Error: {e}")
