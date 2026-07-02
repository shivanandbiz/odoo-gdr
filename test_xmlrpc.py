import xmlrpc.client

url = 'https://biztechnosys1.odoo.com'
db = 'biztechnosys1' # Usually matches the subdomain for SaaS
username = 'shivanand.b@biztechnosys.com'
password = 'Shivu@2467'

print("Attempting to connect to Odoo SaaS...")
try:
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    
    # Authenticate
    uid = common.authenticate(db, username, password, {})
    if not uid:
        print("Auth failed with db='biztechnosys1'. Trying to get db list...")
        # Sometimes getting db list is not allowed on SaaS, but let's try
        try:
            dbs = common.list()
            print("Databases:", dbs)
            for d in dbs:
                uid = common.authenticate(d, username, password, {})
                if uid:
                    print(f"SUCCESS with db: {d}, uid: {uid}")
                    break
        except Exception as e:
            print("List failed:", e)
    else:
        print(f"SUCCESS! Logged in with uid: {uid}")
        
    if uid:
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        
        # Test query
        user_info = models.execute_kw(db, uid, password, 'res.users', 'read', [[uid]], {'fields': ['name', 'login']})
        print("Logged in as:", user_info)
        
        # Check company setup
        companies = models.execute_kw(db, uid, password, 'res.company', 'search_read', [[]], {'fields': ['name', 'currency_id']})
        print("Companies:", companies)
        
except Exception as e:
    print(f"Connection error: {e}")
