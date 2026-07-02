import xmlrpc.client

url = 'https://biztechnosys1.odoo.com'
db = 'biztechnosys1'
username = 'shivanand.b@biztechnosys.com'
password = 'Shivu@2467'

modules_to_check = [
    'calendar', 'appointment', 'project_todo', 'sale_management', 
    'board', 'project', 'purchase', 'stock', 'mrp', 'quality_control', 
    'stock_barcode', 'mrp_plm', 'sign', 'hr', 'hr_payroll', 
    'hr_attendance', 'hr_recruitment', 'hr_holidays', 
    'approvals', 'link_tracker'
]

try:
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, username, password, {})
    if not uid:
        print("Auth failed.")
        exit()
        
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    modules = models.execute_kw(db, uid, password, 'ir.module.module', 'search_read', 
        [[['name', 'in', modules_to_check]]], 
        {'fields': ['name', 'state']})
        
    for mod in modules:
        print(f"Module: {mod['name']:<20} State: {mod['state']}")

except Exception as e:
    print(f"Error: {e}")
