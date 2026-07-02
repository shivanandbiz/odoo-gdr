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
    xl = pd.ExcelFile(fname)
    sheet_names = xl.sheet_names
    print(f"File contains sheets: {sheet_names}")

    print("--- GLOBAL CLEANUP of Payment Register Migration Data ---")
    # Clean up ANY moves starting with PAY_ for the entire year 2025-26
    # This includes PAY_APR_JUNE, PAY_JUL_SEP, PAY_OCT_DEC, PAY_GDR, etc.
    legacy_moves = env['account.move'].search([
        ('ref', 'like', 'PAY_%'),
        ('date', '>=', '2025-04-01'),
        ('date', '<=', '2026-03-31')
    ])
    if legacy_moves:
        print(f"  Removing {len(legacy_moves)} previous migration journal entries...")
        legacy_moves.line_ids.remove_move_reconcile()
        posted = legacy_moves.filtered(lambda m: m.state == 'posted')
        if posted: posted.button_draft()
        legacy_moves.unlink()
        
    # Also clean up linked payments via SQL to be safe
    env.cr.execute("DELETE FROM account_payment WHERE memo LIKE 'PAY_%%'")
    env.cr.execute("DELETE FROM account_move WHERE ref LIKE 'PAY_%%'")
    
    # Clean up blank/Register moves as requested
    env.cr.execute("""
        DELETE FROM account_move 
        WHERE date >= '2025-04-01' AND date <= '2026-03-31'
        AND move_type = 'entry'
        AND (ref IS NULL OR ref = '' OR ref LIKE '%%Register%%')
        AND journal_id IN (SELECT id FROM account_journal WHERE type IN ('bank', 'cash'))
    """)
    
    env.cr.commit()
    print("Cleanup finished.\n")

    sheet_prefix_map = {
        'Apr-June': 'AJ',
        'July-Sep': 'JS',
        'Oct-Dec': 'OD',
        'Jan-March': 'JM'
    }

    total_rows = 0
    total_reconciled = 0
    errors = 0

    for sheet in sheet_names:
        print(f"Processing sheet: {sheet}...")
        df = pd.read_excel(fname, sheet_name=sheet, header=None)
        
        # Headers at Row 9 (Index 8)
        headers = df.iloc[8].tolist()
        accounts_map = {}
        # Data columns start at Index 7 usually in these Tally exports
        for i in range(7, len(headers)):
            if pd.notna(headers[i]):
                accounts_map[i] = str(headers[i]).strip()
        
        sheet_pref = sheet_prefix_map.get(sheet, 'GDR')
        
        # Data starts from Row 10 (Index 9)
        for idx, row in df.iloc[9:].iterrows():
            r = row.tolist()
            if not any(pd.notna(x) for x in r): continue
            
            raw_date = r[0]
            part_name = str(r[1]).strip() if pd.notna(r[1]) else ''
            
            # Use specific ref if available, otherwise generated one
            vref = str(r[3]).strip() if pd.notna(r[3]) else f"{sheet_pref}_{idx}"
            narration = str(r[5]).strip() if pd.notna(r[5]) else ''
            
            if not part_name or 'Total' in part_name or part_name == 'nan': continue

            # Determine amount from accounts columns or Gross Total (Index 6)
            vals = {}
            for col_idx, acc_name in accounts_map.items():
                if col_idx < len(r) and pd.notna(r[col_idx]):
                    try:
                        v = float(r[col_idx] or 0)
                        if v != 0: vals[acc_name] = v
                    except: pass
            
            amount = float(r[6] or 0) if pd.notna(r[6]) else 0
            if amount == 0 and vals:
                amount = sum(abs(v) for v in vals.values())
            
            if amount == 0: continue

            dr_name = None
            cr_name = None
            
            is_bank_source = any(b in part_name for b in ['HDFC', 'Kotak', 'Bank', 'Cash', 'CASH', 'THE KARUR', 'Gkp'])
            
            if is_bank_source:
                cr_name = part_name
                # Find dr_name from accounts_map
                for name in vals.keys():
                    if name != part_name:
                        dr_name = name
                        break
                if not dr_name: dr_name = "Suspense"
            else:
                dr_name = part_name
                # Find cr_name from accounts_map
                for name in vals.keys():
                    if any(b in name for b in ['HDFC', 'Kotak', 'Bank', 'Cash', 'CASH', 'THE KARUR', 'Gkp']):
                        cr_name = name
                        break
                if not cr_name: cr_name = "Bank"

            dt_str = datetime.now().strftime('%Y-%m-%d')
            if isinstance(raw_date, (datetime, pd.Timestamp)):
                dt_str = raw_date.strftime('%Y-%m-%d')
            elif pd.notna(raw_date):
                dt_str = str(raw_date)[:10]

            journal = get_journal(cr_name)
            
            try:
                partner = get_partner(dr_name)
                dr_acc = get_account(dr_name)
                cr_acc = get_account(cr_name)
                
                dr_acc_id = partner.property_account_payable_id.id if partner else (dr_acc.id if dr_acc else False)
                cr_acc_id = cr_acc.id if cr_acc else journal.default_account_id.id
                
                if not dr_acc_id:
                    if not dr_acc:
                        partner = env['res.partner'].create({'name': dr_name, 'supplier_rank': 1})
                        dr_acc_id = partner.property_account_payable_id.id
                    else:
                        dr_acc_id = dr_acc.id

                # Create Posted Journal Entry (Proper Move)
                move = env['account.move'].create({
                    'move_type': 'entry',
                    'date': dt_str,
                    'ref': f"PAY_GDR/{sheet_pref}/{vref}",
                    'journal_id': journal.id,
                    'line_ids': [
                        (0, 0, {
                            'name': f"Payment: {dr_name} | {narration}",
                            'account_id': dr_acc_id,
                            'debit': amount,
                            'credit': 0.0,
                            'partner_id': partner.id if partner else False,
                        }),
                        (0, 0, {
                            'name': f"Payment: {dr_name} | {narration}",
                            'account_id': cr_acc_id,
                            'debit': 0.0,
                            'credit': amount,
                        }),
                    ]
                })
                move.action_post()
                
                total_rows += 1
                
                # Reconciliation
                if partner:
                    pay_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled)
                    bill_lines = env['account.move.line'].search([
                        ('partner_id', '=', partner.id),
                        ('account_id.account_type', '=', 'liability_payable'),
                        ('reconciled', '=', False),
                        ('move_id.move_type', '=', 'in_invoice'),
                        ('move_id.state', '=', 'posted'),
                        ('credit', '>', 0)
                    ], order='date asc')
                    if pay_line and bill_lines:
                        (pay_line | bill_lines).reconcile()
                        total_reconciled += 1
                        
            except Exception as e:
                errors += 1
                print(f"  ERR row {idx} in {sheet}: {e}")
        
        print(f"  Sheet {sheet} finished. Migrated: {total_rows} so far.")
        env.cr.commit()

    print(f"\nAll GDR Payment Registers Migrated.")
    print(f"Total: {total_rows} | Reconciled: {total_reconciled} | Errors: {errors}")

migrate_gdr_payments()
