import pandas as pd
from datetime import datetime

def get_partner(name):
    if not name: return None
    p = env['res.partner'].search([('name', '=ilike', name)], limit=1)
    if not p:
        p = env['res.partner'].search([('name', 'ilike', name)], limit=1)
    return p

def get_account(name):
    if not name: return None
    return env['account.account'].search([('name', 'ilike', name)], limit=1)

def get_journal(name):
    j = env['account.journal'].search([('name', 'ilike', name)], limit=1)
    if not j:
        j = env['account.journal'].search([('code', '=', 'BNK1')], limit=1)
        if not j: j = env['account.journal'].search([('type', '=', 'bank')], limit=1)
    return j

def migrate_gdr_payments():
    fname = '/home/biz/odoo/payment_register_gdr.xlsx'
    xl_file = pd.ExcelFile(fname)
    sheet_names = xl_file.sheet_names
    print(f"File contains sheets: {sheet_names}")

    print("--- GLOBAL CLEANUP (Odoo API) ---")
    prefixes = ['PAY_GDR/', 'PAY_APR_JUNE/', 'PAY_JUL_SEP/', 'PAY_OCT_DEC/', 'AJ_', 'JS_', 'OD_', 'JM_']
    for pref in prefixes:
        moves = env['account.move'].search([('ref', 'like', f"{pref}%")])
        if moves:
            print(f"  Removing {len(moves)} moves with prefix {pref}")
            moves.line_ids.remove_move_reconcile()
            moves.filtered(lambda m: m.state == 'posted').button_draft()
            moves.unlink()
            
        payments = env['account.payment'].search([('memo', 'like', f"{pref}%")])
        if payments:
            print(f"  Removing {len(payments)} payments with prefix {pref}")
            # Ensure payments are in draft before unlink
            payments.filtered(lambda p: p.state != 'draft').action_draft()
            payments.unlink()
            
    # Also clean up unreferenced moves in the periods
    ghost_moves = env['account.move'].search([
        ('date', '>=', '2025-04-01'),
        ('date', '<=', '2026-03-31'),
        ('move_type', '=', 'entry'),
        ('ref', '=', False),
        ('journal_id.type', 'in', ['bank', 'cash'])
    ])
    if ghost_moves:
        print(f"  Removing {len(ghost_moves)} ghost journal entries...")
        ghost_moves.line_ids.remove_move_reconcile()
        ghost_moves.filtered(lambda m: m.state == 'posted').button_draft()
        ghost_moves.unlink()

    env.cr.commit()
    print("Cleanup finished.\n")

    sheet_prefix_map = {
        'Apr-June': 'AJ',
        'July-Sep': 'JS',
        'Oct-Dec': 'OD',
        'Jan-March': 'JM'
    }

    total_count = 0
    total_reconciled = 0
    errors = 0

    for sheet in sheet_names:
        print(f"Processing sheet: {sheet}...")
        df = pd.read_excel(fname, sheet_name=sheet, header=None)
        
        # 1. Dynamic Header/Data Detection
        headers = None
        data_start_idx = 9
        for i in range(7, 12):
            if i >= len(df): break
            row_vals = [str(x).strip() for x in df.iloc[i].tolist()]
            if 'Date' in row_vals and 'Particulars' in row_vals:
                headers = row_vals
                data_start_idx = i + 1
                break
        
        if not headers:
            print(f"  CRITICAL: Could not find headers in {sheet}, skipping.")
            continue
            
        # 2. Map Columns
        col_map = {h: i for i, h in enumerate(headers) if h != 'nan'}
        amount_idx = col_map.get('Gross Total', col_map.get('Value', 6))
        part_idx = col_map.get('Particulars', 1)
        date_idx = col_map.get('Date', 0)
        ref_idx = col_map.get('Voucher Ref. No.', 3)
        narr_idx = col_map.get('Narration', 5)
        
        accounts_map = {}
        for i, h in enumerate(headers):
            if i >= 7 and h != 'nan' and h not in ['Gross Total', 'Value', 'Voucher Ref. No.', 'Voucher Ref. Date', 'Narration']:
                accounts_map[i] = h
        
        sheet_pref = sheet_prefix_map.get(sheet, 'GDR')
        
        print(f"  Found headers at Row {data_start_idx}. Amount column index: {amount_idx}")

        # 3. Iterate Data
        for idx, row in df.iloc[data_start_idx:].iterrows():
            r = row.tolist()
            if not any(pd.notna(x) for x in r): continue
            
            raw_date = r[date_idx]
            part_name = str(r[part_idx]).strip() if pd.notna(r[part_idx]) else ''
            
            raw_ref = str(r[ref_idx]).strip() if pd.notna(r[ref_idx]) else ''
            vref_suffix = raw_ref[:50] if raw_ref and len(raw_ref) < 100 else f"{idx}"
            
            narration = str(r[narr_idx]).strip() if pd.notna(r[narr_idx]) else ''
            
            if not part_name or 'Total' in part_name or part_name == 'nan': continue

            try:
                amount = float(r[amount_idx] or 0)
            except:
                amount = 0
                
            if amount == 0:
                for col_i in accounts_map.keys():
                    try:
                        v = float(r[col_i] or 0)
                        if v != 0:
                            amount = abs(v)
                            break
                    except: pass
            
            if amount == 0: continue

            dr_name = part_name
            cr_name = "Bank"
            is_bank_source = any(b in part_name for b in ['HDFC', 'Kotak', 'Bank', 'Cash', 'CASH', 'THE KARUR', 'Gkp'])
            
            if is_bank_source:
                cr_name = part_name
                for col_i, acc_name in accounts_map.items():
                    if float(r[col_i] or 0) != 0 and acc_name != part_name:
                        dr_name = acc_name
                        break
            else:
                dr_name = part_name
                for col_i, acc_name in accounts_map.items():
                    if float(r[col_i] or 0) != 0:
                        if any(b in acc_name for b in ['HDFC', 'Kotak', 'Bank', 'Cash', 'CASH', 'THE KARUR', 'Gkp']):
                            cr_name = acc_name
                            break

            journal = get_journal(cr_name)
            
            dt_str = datetime.now().strftime('%Y-%m-%d')
            if isinstance(raw_date, (datetime, pd.Timestamp)):
                dt_str = raw_date.strftime('%Y-%m-%d')
            elif pd.notna(raw_date):
                dt_str = str(raw_date)[:10]

            try:
                partner = get_partner(dr_name)
                
                # Create PROPER Payment record
                payment = env['account.payment'].create({
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'partner_id': partner.id if partner else False,
                    'amount': amount,
                    'journal_id': journal.id,
                    'date': dt_str,
                    'memo': f"PAY_GDR/{sheet_pref}/{vref_suffix} | {narration}"[:255],
                })
                
                payment.action_post()
                total_count += 1
                
                # Reconciliation
                if partner:
                    bill_lines = env['account.move.line'].search([
                        ('partner_id', '=', partner.id),
                        ('account_id.account_type', '=', 'liability_payable'),
                        ('reconciled', '=', False),
                        ('move_id.move_type', '=', 'in_invoice'),
                        ('move_id.state', '=', 'posted'),
                        ('credit', '>', 0)
                    ], order='date asc')
                    pay_line = payment.move_id.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled)
                    if pay_line and bill_lines:
                        (pay_line | bill_lines).reconcile()
                        total_reconciled += 1
                        
            except Exception as e:
                errors += 1
                print(f"  ERR row {idx} in {sheet}: {e}")
            
            if total_count % 100 == 0:
                print(f"  Processing: {total_count} payments created...")

        print(f"  Sheet {sheet} finished. Running Total: {total_count} payments.")
        env.cr.commit()

    print(f"\nFINAL MIGRATION COMPLETE.")
    print(f"Total Payments in GUI: {total_count}")
    print(f"Total Reconciled: {total_reconciled}")
    print(f"Errors: {errors}")

migrate_gdr_payments()
