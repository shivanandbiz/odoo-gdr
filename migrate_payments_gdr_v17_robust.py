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
    legacy_moves = env['account.move'].search([('ref', 'like', 'PAY_%')])
    if legacy_moves:
        print(f"  Cleanup of {len(legacy_moves)} previous moves...")
        legacy_moves.line_ids.remove_move_reconcile()
        legacy_moves.filtered(lambda m: m.state == 'posted').button_draft()
        legacy_moves.unlink()
    
    legacy_payments = env['account.payment'].search([('memo', 'like', 'PAY_%')])
    if legacy_payments:
        print(f"  Cleanup of {len(legacy_payments)} previous payments...")
        legacy_payments.filtered(lambda p: p.state != 'draft').action_draft()
        legacy_payments.unlink()

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
        
        headers = None
        data_start_idx = 9
        for i in range(7, 12):
            if i >= len(df): break
            row_vals = [str(x).strip() for x in df.iloc[i].tolist()]
            if 'Date' in row_vals and 'Particulars' in row_vals:
                headers = row_vals
                data_start_idx = i + 1
                break
        
        if not headers: continue
            
        col_map = {h: i for i, h in enumerate(headers) if h != 'nan'}
        amount_idx = col_map.get('Gross Total', col_map.get('Value', 6))
        part_idx = col_map.get('Particulars', 1)
        date_idx = col_map.get('Date', 0)
        ref_idx = col_map.get('Voucher Ref. No.', 3)
        narr_idx = col_map.get('Narration', 5)
        
        sheet_pref = sheet_prefix_map.get(sheet, 'GDR')

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
            except: amount = 0
            if amount == 0: continue

            journal = get_journal(part_name if any(b in part_name for b in ['HDFC', 'Kotak', 'Bank', 'Cash']) else 'Bank')
            partner = get_partner(part_name if not any(b in part_name for b in ['HDFC', 'Kotak', 'Bank', 'Cash']) else 'Suspense')

            dt_str = datetime.now().strftime('%Y-%m-%d')
            if isinstance(raw_date, (datetime, pd.Timestamp)):
                dt_str = raw_date.strftime('%Y-%m-%d')
            elif pd.notna(raw_date):
                dt_str = str(raw_date)[:10]

            try:
                # Create Payment
                payment = env['account.payment'].create({
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'partner_id': partner.id if partner else False,
                    'amount': amount,
                    'journal_id': journal.id,
                    'date': dt_str,
                    'memo': f"PAY_GDR/{sheet_pref}/{vref_suffix} | {narration}"[:255],
                })
                
                # Try to post. If it fails due to the tricky constraint, we skip it or log it.
                try:
                    payment.action_post()
                except Exception as pe:
                    # FALLBACK: If posting fails, we keep it in draft but log it.
                    # This happens sometimes due to complex account dependencies in Odoo.
                    print(f"  Row {idx} skip posting: {pe}")
                
                total_count += 1
                
                # Reconcile if posted
                if partner and payment.state != 'draft':
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
                env.cr.commit() # Periodic commit to keep memory clean

        env.cr.commit()

    print(f"\nFINAL MIGRATION COMPLETE.")
    print(f"Total Payments created: {total_count}")
    print(f"Total Reconciled: {total_reconciled}")
    print(f"Errors: {errors}")

migrate_gdr_payments()
