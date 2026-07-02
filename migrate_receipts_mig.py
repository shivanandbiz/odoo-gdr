import pandas as pd
from datetime import datetime

def get_partner(name):
    # Strictly match by name
    return env['res.partner'].search([('name', '=', name)], limit=1)

def get_account(name):
    # Check by name
    return env['account.account'].search([('name', 'ilike', name)], limit=1)

def migrate_receipts_mig():
    fname = '/home/biz/odoo/new_recipt_register_mig.xlsx'
    print(f"Reading {fname} with pandas...")
    df = pd.read_excel(fname, header=None)
    
    # Mapping of column indices to account names from Row 9
    dest_map = {
        8: 'HDFC C/A 50200024612749',
        9: 'Kotak -3545975369',
        10: 'Gkp Current A/c',
        11: 'BANK CHARGES',
        12: 'Imprest - Shantalinga',
        13: 'BG Rail Bhavan -009GT02231400001',
        14: 'FD INTEREST',
        15: 'Cholamandalam Investment and Finance Cmpy LTD Term',
        16: 'F D Amount',
        17: 'Suspense',
        18: 'THE KARUR VYSYA BANK LIMITED -Unsecured'
    }

    journal = env['account.journal'].search([('code', '=', 'BNK1')], limit=1)
    if not journal:
        journal = env['account.journal'].search([('type', '=', 'bank')], limit=1)

    print("Cleaning up previous migration entries (ref like REC_MIG/)...")
    existing = env['account.move'].search([('ref', 'like', 'REC_MIG/%')])
    if existing:
        for m in existing:
            if m.state != 'draft': m.button_draft()
        existing.unlink()
        env.cr.commit()
    
    count = 0
    reconciled_count = 0
    errors = 0
    
    # Data starts from row 10 (index 9)
    for idx, row in df.iloc[9:].iterrows():
        r = row.tolist()
        if not any(pd.notna(x) for x in r): continue
        
        raw_date = r[0]
        part_name = str(r[1]).strip() if pd.notna(r[1]) else ''
        vref = str(r[3]).strip() if pd.notna(r[3]) and str(r[3]) != 'nan' else f"{idx}"
        narration = str(r[5]).strip() if pd.notna(r[5]) else ''
        
        if not part_name or 'Total' in part_name or part_name == 'nan': continue
        
        # Determine Destination Account and Amount
        dest_account_name = None
        amount = 0.0
        for col_idx in range(8, 19):
            if col_idx < len(r) and pd.notna(r[col_idx]) and float(r[col_idx] or 0) > 0:
                dest_account_name = dest_map.get(col_idx)
                amount = float(r[col_idx])
                break
        
        if amount == 0: continue
        
        if isinstance(raw_date, (datetime, pd.Timestamp)):
            dt_str = raw_date.strftime('%Y-%m-%d')
        else:
            try:
                dt_str = str(raw_date)[:10]
            except:
                dt_str = datetime.now().strftime('%Y-%m-%d')
        
        # ── DESTINATION ACCOUNT ─────────────────────────────────────────
        dest_acc = get_account(dest_account_name)
        if not dest_acc:
            # Fallback to journal default account
            dest_acc_id = journal.default_account_id.id
        else:
            dest_acc_id = dest_acc.id

        # ── SOURCE (PARTICULARS) ────────────────────────────────────────
        partner = get_partner(part_name)
        # Check if Part Name is one of our bank accounts (Transfer Case)
        is_transfer = any(part_name.lower() in val.lower() for val in dest_map.values())
        
        partner_id = False
        source_acc_id = False
        
        if partner:
            partner_id = partner.id
            source_acc_id = partner.property_account_receivable_id.id
        elif is_transfer:
            # Look for bank account
            source_acc = get_account(part_name)
            if source_acc:
                source_acc_id = source_acc.id
            else:
                # Still use partner fallback?
                p = env['res.partner'].search([('name', '=', part_name)], limit=1)
                if not p: p = env['res.partner'].create({'name': part_name})
                partner_id = p.id
                source_acc_id = p.property_account_receivable_id.id
        else:
            # Fallback: create partner
            p = env['res.partner'].search([('name', '=', part_name)], limit=1)
            if not p: p = env['res.partner'].create({'name': part_name, 'customer_rank': 1})
            partner_id = p.id
            source_acc_id = p.property_account_receivable_id.id
            
        try:
            line_ids = [
                (0, 0, {
                    'name': f"Receipt: {part_name} | {narration}",
                    'account_id': dest_acc_id,
                    'debit': amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': f"Receipt: {part_name} | {narration}",
                    'account_id': source_acc_id,
                    'partner_id': partner_id,
                    'debit': 0.0,
                    'credit': amount,
                }),
            ]
            
            move = env['account.move'].create({
                'move_type': 'entry',
                'date': dt_str,
                'ref': f"REC_MIG/{vref}",
                'journal_id': journal.id,
                'line_ids': line_ids,
            })
            move.action_post()
            count += 1
            
            # ── RECONCILIATION ───────────────────────────────────────────
            if partner_id:
                rec_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
                if rec_line:
                    open_lines = env['account.move.line'].search([
                        ('partner_id', '=', partner_id),
                        ('account_id', '=', source_acc_id),
                        ('reconciled', '=', False),
                        ('move_id.move_type', '=', 'out_invoice'),
                        ('move_id.state', '=', 'posted'),
                        ('balance', '>', 0)
                    ], order='date asc')
                    if open_lines:
                        (rec_line | open_lines).reconcile()
                        reconciled_count += 1
                        
        except Exception as e:
            errors += 1
            print(f"  ERR row {idx}: {e}")
            
    env.cr.commit()
    print(f"\nMigration Finished. Total: {count} | Reconciled: {reconciled_count} | Errors: {errors}")

migrate_receipts_mig()
