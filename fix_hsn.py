import xmlrpc.client

url = 'https://biztechnosys1.odoo.com'
db = 'biztechnosys1'
username = 'shivanand.b@biztechnosys.com'
password = 'Shivu@2467'

try:
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, username, password, {})
        
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    # Enable GST Registration for the company
    success = models.execute_kw(db, uid, password, 'res.company', 'write', 
        [[1], {'l10n_in_is_gst_registered': True}])
    print(f"Company updated successfully: {success}")
    
    # Check if a product now shows l10n_in_is_gst_registered_enabled
    products = models.execute_kw(db, uid, password, 'product.template', 'search_read', 
        [[]], 
        {'fields': ['name', 'l10n_in_is_gst_registered_enabled', 'fiscal_country_codes'], 'limit': 1})
    print("\nProduct after update:", products)

except Exception as e:
    print(f"Error: {e}")
