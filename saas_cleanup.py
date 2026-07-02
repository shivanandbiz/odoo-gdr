import xmlrpc.client

url = 'https://biztechnosys1.odoo.com'
db = 'biztechnosys1'
username = 'shivanand.b@biztechnosys.com'
password = 'Shivu@2467'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def clean_and_resync():
    print("--- 1. Searching for previously submitted generic entries ---")
    # Finding moves that we created with move_type 'entry' on or after 2025-04-01
    domain = [('date', '>=', '2025-04-01'), ('move_type', '=', 'entry'), ('state', '=', 'posted')]
    remote_moves = models.execute_kw(db, uid, password, 'account.move', 'search', [domain])
    
    print(f"Found {len(remote_moves)} remote posted entry moves to clean up.")
    if remote_moves:
        print("Reverting them to draft...")
        # Step 1: Button Draft
        # Wait, Odoo 17 action_draft might require 'button_draft' method
        try:
            models.execute_kw(db, uid, password, 'account.move', 'button_draft', [remote_moves])
        except Exception as e:
            print("Drafting failed natively over XML-RPC, they might already be draft or button_draft isn't exposed:", e)
            
        print("Deleting them...")
        try:
            models.execute_kw(db, uid, password, 'account.move', 'unlink', [remote_moves])
            print("Cleanup successful.")
        except Exception as e:
            print("Unlink failed:", e)
            
clean_and_resync()
