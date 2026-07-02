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

    print("--- GLOBAL CLEANUP ---")
    # Using SQL for speed and ensuring total clearance
    env.cr.execute("UPDATE account_move_line SET reconcile_model_id = NULL WHERE reconcile_model_id IS NOT NULL")
    env.cr.execute("DELETE FROM account_partial_reconcile")
    env.cr.execute("DELETE FROM account_full_reconcile")
    
    # Clean up prefixes
    prefixes = ['PAY_APR_JUNE/', 'PAY_JUL_SEP/', 'PAY_OCT_DEC/', 'PAY_GDR/', 'AJ_', 'JS_', 'OD_', 'JM_']
    for pref in prefixes:
        # We need to set state to draft to allow deletion (SQL is faster)
        env.cr.execute("UPDATE account_move SET state = 'draft' WHERE ref LIKE %s", (f"{pref}%",))
        env.cr.execute("DELETE FROM account_move_line WHERE move_id IN (SELECT id FROM account_move WHERE ref LIKE %s)", (f"{pref}%",))
        env.cr.execute("DELETE FROM account_move WHERE ref LIKE %s", (f"{pref}%",))
        
        env.cr.execute("UPDATE account_payment SET state = 'draft' WHERE memo LIKE %s", (f"{pref}%",))
        env.cr.execute("DELETE FROM account_payment WHERE memo LIKE %s", (f"{pref}%",))
    
    # Generic cleanup for the period to avoid ghost data
    env.cr.execute("""
        UPDATE account_move SET state = 'draft' 
        WHERE date >= '2025-04-01' AND date <= '2026-03-31'
        AND move_type = 'entry'
        AND (ref IS NULL OR ref = '' OR ref LIKE '%%Register%%')
    """)
    env.cr.execute("""
        DELETE FROM account_move_line 
        WHERE move_id IN (SELECT id FROM account_move WHERE date >= '2025-04-01' AND date <= '2026-03-31' AND move_type = 'entry' AND (ref IS NULL OR ref = ''))
    """)
    env.cr.execute("""
        DELETE FROM account_move 
        WHERE date >= '2025-04-01' AND date <= '2026-03-31'
        AND move_type = 'entry'
        AND (ref IS NULL OR ref = '')
    """)
    
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
        
        headers = df.iloc[8].tolist()
        accounts_map = {}
        for i in range(7, len(headers)):
            if pd.notna(headers[i]):
                accounts_map[i] = str(headers[i]).strip()
        
        sheet_pref = sheet_prefix_map.get(sheet, 'GDR')
        
        for idx, row in df.iloc[9:].iterrows():
            r = row.tolist()
            if not any(pd.notna(x) for x in r): continue
            
            raw_date = r[0]
            part_name = str(r[1]).strip() if pd.notna(r[1]) else ''
            vref = str(r[3]).strip() if pd.notna(r[3]) else f"{sheet_pref}_{idx}"
            narration = str(r[5]).strip() if pd.notna(r[5]) else ''
            
            if not part_name or 'Total' in part_name or part_name == 'nan': continue

            # Determine amount from Gross Total (Index 6)
            amount = float(r[6] or 0) if pd.notna(r[6]) else 0
            if amount == 0: continue

            dr_name = part_name
            cr_name = "Bank" # Default

            is_bank_source = any(b in part_name for b in ['HDFC', 'Kotak', 'Bank', 'Cash', 'CASH', 'THE KARUR', 'Gkp'])
            
            if is_bank_source:
                cr_name = part_name
                # Look for dr_name in accounts columns
                for col_idx, acc_name in accounts_map.items():
                    if col_idx < len(r) and pd.notna(r[col_idx]) and float(r[col_idx] or 0) != 0:
                        if acc_name != part_name:
                            dr_name = acc_name
                            break
            else:
                dr_name = part_name
                # Look for cr_name in accounts columns
                for col_idx, acc_name in accounts_map.items():
                    if col_idx < len(r) and pd.notna(r[col_idx]) and float(r[col_idx] or 0) != 0:
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
                
                # Create PROPER Payment record so it shows in the "Vendor Payments" menu
                payment = env['account.payment'].create({
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'partner_id': partner.id if partner else False,
                    'amount': amount,
                    'journal_id': journal.id,
                    'date': dt_str,
                    'memo': f"PAY_GDR/{sheet_pref}/{vref} | {narration}",
                })
                
                # Post the payment. This generates the sequence and moves.
                payment.action_post()
                
                total_count += 1
                
                # Reconciliation with Vendor Bills
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

        print(f"  Sheet {sheet} finished. Migrated: {total_count} payments.")
        env.cr.commit()

    print(f"\nFinal Migration Result:")
    print(f"Total Payments in 'Vendor Payments' menu: {total_count}")
    print(f"Total Reconciled with Bills: {total_reconciled}")
    print(f"Errors: {errors}")

migrate_gdr_payments()
