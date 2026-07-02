import xmlrpc.client

url = 'https://biztechnosys1.odoo.com'
db = 'biztechnosys1'
username = 'shivanand.b@biztechnosys.com'
password = 'Shivu@2467'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def sync_ledger_v2():
    print("--- Mapping Partners ---")
    rem_parts = models.execute_kw(db, uid, password, 'res.partner', 'search_read', [[]], {'fields': ['name']})
    rem_part_map = {p['name'].lower(): p['id'] for p in rem_parts if p.get('name')}
    
    # --- Sync Accounts ---
    print("--- Syncing Accounts ---")
    local_accs = env['account.account'].search([])
    rem_accs = models.execute_kw(db, uid, password, 'account.account', 'search_read', [[]], {'fields': ['name', 'code']})
    rem_acc_map = {a['name'].lower(): a['id'] for a in rem_accs if a.get('name')}
    rem_code_map = {a['code']: a['id'] for a in rem_accs if a.get('code')}
    
    accs_to_create = []
    for a in local_accs:
        if a.name.lower() not in rem_acc_map and a.code not in rem_code_map:
            accs_to_create.append({
                'name': a.name,
                'code': a.code,
                'account_type': a.account_type,
            })
    
    if accs_to_create:
        print(f"Creating {len(accs_to_create)} missing accounts individually...")
        for ac in accs_to_create:
            try: models.execute_kw(db, uid, password, 'account.account', 'create', [[ac]])
            except: pass
                
    rem_accs = models.execute_kw(db, uid, password, 'account.account', 'search_read', [[]], {'fields': ['name', 'code']})
    rem_acc_map = {a['name'].lower(): a['id'] for a in rem_accs if a.get('name')}
    rem_code_map = {a['code']: a['id'] for a in rem_accs if a.get('code')}

    # --- Sync Journals ---
    print("--- Syncing Journals ---")
    local_js = env['account.journal'].search([])
    rem_js = models.execute_kw(db, uid, password, 'account.journal', 'search_read', [[]], {'fields': ['name', 'code']})
    rem_j_map = {j['name'].lower(): j['id'] for j in rem_js if j.get('name')}
    rem_jcode_map = {j['code']: j['id'] for j in rem_js if j.get('code')}
    
    js_to_create = []
    for j in local_js:
        if j.name.lower() not in rem_j_map and j.code not in rem_jcode_map:
            js_to_create.append({
                'name': j.name,
                'code': j.code,
                'type': j.type,
            })
    if js_to_create:
        print(f"Creating {len(js_to_create)} missing journals individually...")
        for jc in js_to_create:
            try: models.execute_kw(db, uid, password, 'account.journal', 'create', [[jc]])
            except: pass

    rem_js = models.execute_kw(db, uid, password, 'account.journal', 'search_read', [[]], {'fields': ['name', 'code']})
    rem_jcode_map = {j['code']: j['id'] for j in rem_js if j.get('code')}
    
    # Sync Moves (Using move_type='entry')
    print("--- Syncing Moves & Lines ---")
    local_moves = env['account.move'].search([('state', '=', 'posted'), ('date', '>=', '2025-04-01')])
    print(f"Total Local Posted Moves: {len(local_moves)}")
    
    moves_to_create = []
    count = 0
    err_count = 0
    
    for m in local_moves:
        r_journal_id = rem_jcode_map.get(m.journal_id.code)
        if not r_journal_id: r_journal_id = list(rem_jcode_map.values())[0] if rem_jcode_map else 1
        
        move_payload = {
            'move_type': 'entry',
            'date': m.date.strftime('%Y-%m-%d') if m.date else '2025-04-01',
            'ref': m.ref or m.name or "MIG",
            'journal_id': r_journal_id,
            'line_ids': []
        }
        
        valid_lines = True
        for l in m.line_ids:
            if not l.account_id.name: continue
            
            # Map elements precisely
            r_acc_id = rem_code_map.get(l.account_id.code) or rem_acc_map.get(l.account_id.name.lower())
            if not r_acc_id: 
                valid_lines = False; break
            
            r_part_id = False
            if l.partner_id and l.partner_id.name:
                r_part_id = rem_part_map.get(l.partner_id.name.lower(), False)
                
            move_payload['line_ids'].append((0, 0, {
                'name': l.name or 'Migrated Line',
                'account_id': r_acc_id,
                'partner_id': r_part_id,
                'debit': l.debit,
                'credit': l.credit,
            }))
            
        if valid_lines and move_payload['line_ids']:
            moves_to_create.append(move_payload)
            count += 1
            
            # Flush batch every 50 for safety
            if len(moves_to_create) >= 50:
                print(f"Pushing Batch of 50 Moves... (Total Configured: {count})")
                try: 
                    new_move_ids = models.execute_kw(db, uid, password, 'account.move', 'create', [moves_to_create])
                    models.execute_kw(db, uid, password, 'account.move', 'action_post', [new_move_ids])
                except Exception as e:
                    print(f"Batch fail ({str(e)[:100]}), doing individually...")
                    for single_m in moves_to_create:
                        try:
                            cm = models.execute_kw(db, uid, password, 'account.move', 'create', [[single_m]])
                            models.execute_kw(db, uid, password, 'account.move', 'action_post', [cm])
                        except Exception as e2: err_count += 1
                moves_to_create = []

    if moves_to_create:
        print(f"Pushing Final Batch of {len(moves_to_create)} Moves...")
        try: 
            new_move_ids = models.execute_kw(db, uid, password, 'account.move', 'create', [moves_to_create])
            models.execute_kw(db, uid, password, 'account.move', 'action_post', [new_move_ids])
        except Exception as e:
            for single_m in moves_to_create:
                try:
                    cm = models.execute_kw(db, uid, password, 'account.move', 'create', [[single_m]])
                    models.execute_kw(db, uid, password, 'account.move', 'action_post', [cm])
                except Exception as e2: err_count += 1
                
    print(f"\n--- SaaS Ledgers Synchronized! Processed {count} moves. Errors: {err_count} ---")

sync_ledger_v2()
