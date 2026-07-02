import xmlrpc.client

url = 'https://biztechnosys1.odoo.com'
db = 'biztechnosys1'
username = 'shivanand.b@biztechnosys.com'
password = 'Shivu@2467'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def sync_payments_natively():
    print("--- 1. Deleting previously synced payment moves ---")
    rem_payment_moves = models.execute_kw(db, uid, password, 'account.move', 'search', [[
        '|', ('ref', 'ilike', 'PAY_GDR%'), ('ref', 'ilike', 'REC_MIG%')
    ]])
    print(f"Found {len(rem_payment_moves)} remote synced payment moves to delete.")
    if rem_payment_moves:
        models.execute_kw(db, uid, password, 'account.move', 'button_draft', [rem_payment_moves])
        try:
            models.execute_kw(db, uid, password, 'account.move', 'unlink', [rem_payment_moves])
            print("Successfully deleted synced payment moves!")
        except Exception as e:
            print("Unlink failed, possibly some are tied up:", e)
            
    print("\n--- 2. Building Native Payment Sync ---")
    # Fetch maps
    rem_parts = models.execute_kw(db, uid, password, 'res.partner', 'search_read', [[]], {'fields': ['name']})
    rem_part_map = {p['name'].lower(): p['id'] for p in rem_parts if p.get('name')}
    
    rem_js = models.execute_kw(db, uid, password, 'account.journal', 'search_read', [[]], {'fields': ['name', 'code']})
    rem_jcode_map = {j['code']: j['id'] for j in rem_js if j.get('code')}
    
    local_payments = env['account.payment'].search([('state', 'not in', ('draft', 'cancel'))])
    print(f"Total Local Posted Payments to Push: {len(local_payments)}")
    
    payments_to_create = []
    count = 0
    for p in local_payments:
        r_journal_id = rem_jcode_map.get(p.journal_id.code, 1) # Fallback to 1 if not found
        
        r_part_id = False
        if p.partner_id and p.partner_id.name:
            r_part_id = rem_part_map.get(p.partner_id.name.lower(), False)
            
        payload = {
            'amount': p.amount,
            'date': p.date.strftime('%Y-%m-%d'),
            'journal_id': r_journal_id,
            'partner_id': r_part_id,
            'payment_type': p.payment_type,
            'partner_type': p.partner_type,
            'ref': p.ref or p.memo or "MIG",
            'currency_id': 20, # Explicitly INR
        }
        payments_to_create.append(payload)
        count += 1
        
    if payments_to_create:
        print(f"Pushing {len(payments_to_create)} Payments to SaaS Natively...")
        err_count = 0
        success_count = 0
        # Push individually so one failure doesn't stop the rest
        for pay in payments_to_create:
            try:
                np = models.execute_kw(db, uid, password, 'account.payment', 'create', [[pay]])
                models.execute_kw(db, uid, password, 'account.payment', 'action_post', [np])
                success_count += 1
            except Exception as e:
                err_count += 1
                
        print(f"SUCCESS: {success_count} | ERRORS: {err_count}")

sync_payments_natively()
