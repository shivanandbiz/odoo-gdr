import xmlrpc.client

url = 'https://biztechnosys1.odoo.com'
db = 'biztechnosys1'
username = 'shivanand.b@biztechnosys.com'
password = 'Shivu@2467'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def sync_partners():
    print("--- Syncing Partners ---")
    local_partners = env['res.partner'].search([('active', '=', True)])
    print(f"Found {len(local_partners)} local partners to process.")
    
    # Get remote partners to avoid duplicates
    remote_partners = models.execute_kw(db, uid, password, 'res.partner', 'search_read', [[]], {'fields': ['name']})
    remote_map = {p['name'].lower(): p['id'] for p in remote_partners if p.get('name')}
    
    to_create = []
    created_count = 0
    for p in local_partners:
        if not p.name: continue
        name_lower = p.name.lower()
        if name_lower not in remote_map:
            to_create.append({
                'name': p.name,
                'supplier_rank': p.supplier_rank,
                'customer_rank': p.customer_rank,
                'is_company': p.is_company,
            })
    
    print(f"{len(to_create)} matching partners need to be created remotely...")
    if to_create:
        try:
            # Batch create
            models.execute_kw(db, uid, password, 'res.partner', 'create', [to_create])
            print("Successfully created partners in SaaS!")
        except Exception as e:
            print(f"Failed bulk create. Trying individual... Error: {e}")
            for c in to_create:
                try: models.execute_kw(db, uid, password, 'res.partner', 'create', [[c]]); created_count+=1
                except: pass
            print(f"Completed Individual Creates: {created_count}")
    else:
        print("Partners are already perfectly synced.")

sync_partners()
