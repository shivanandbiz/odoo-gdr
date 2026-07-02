# migrate_everything_v1.py
import openpyxl
from datetime import datetime

# 1. SETUP ODOO HELPERS
def get_account_type(name):
    # Simple heuristic for account types
    name = name.lower()
    if any(k in name for k in ['bank', 'cash', 'hdfc', 'kotak', 'indian bank', 'petty']):
        return 'asset_cash'
    if any(k in name for k in ['gst', 'cgst', 'sgst', 'igst', 'tax']):
        return 'asset_current' # Or liability depending on balance, but current asset is safe
    if any(k in name for k in ['capital']):
        return 'equity'
    if any(k in name for k in ['loan']):
        return 'liability_non_current'
    if any(k in name for k in ['payable', 'creditors', 'serivce']):
        return 'liability_payable'
    if any(k in name for k in ['receivable', 'debtors', 'railway']):
        return 'asset_receivable'
    if any(k in name for k in ['expense', 'rent', 'salary', 'fees']):
        return 'expense'
    if any(k in name for k in ['income', 'sales', 'discount']):
        return 'income'
    return 'asset_current' # Default

def get_or_create_account(name):
    account = env['account.account'].search([('name', '=', name)], limit=1)
    if not account:
        type_code = get_account_type(name)
        # Find a free code in the appropriate range
        # (This is simplified, in production you'd want a more robust code generator)
        last_account = env['account.account'].search([('account_type', '=', type_code)], order='code desc', limit=1)
        new_code = str(int(last_account.code) + 1) if last_account else '999999'
        account = env['account.account'].create({
            'name': name,
            'code': new_code,
            'account_type': type_code,
        })
    return account

def get_or_create_journal(name, type):
    journal = env['account.journal'].search([('name', '=', name)], limit=1)
    if not journal:
        journal = env['account.journal'].create({
            'name': name,
            'code': name[:5].upper(),
            'type': type,
        })
    return journal

# 2. EXCEL LOADER
def load_sheet_as_dicts(filename, sheet_name):
    wb = openpyxl.load_workbook(filename, read_only=True, data_only=True)
    ws = wb[sheet_name]
    
    # Headers are on Row 9 (0-indexed 8)
    headers = []
    data_started = False
    rows = []
    
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 8: # Row 9
            headers = [str(h).strip() if h else f"Col_{j}" for j, h in enumerate(row)]
            continue
        if i < 9: continue
        
        # Check if row is empty or footer
        if not row or all(v is None for v in row): continue
        if row[0] and 'Total' in str(row[0]): break
        
        d = dict(zip(headers, row))
        rows.append(d)
    return rows

# 3. MIGRATION LOGIC
def migrate():
    filename = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
    
    # Misc/Default Journals
    j_misc = env['account.journal'].search([('type', '=', 'general')], limit=1)
    j_bank = env['account.journal'].search([('type', '=', 'bank')], limit=1)
    
    # Registers to process
    registers = [
        {'name': 'Contra Register', 'type': 'columnar'},
        {'name': 'Debit Note Register', 'type': 'columnar'},
        {'name': 'Journal Register', 'type': 'columnar'},
        {'name': 'Credit Note Register', 'type': 'columnar'},
        {'name': 'Receipt Register', 'type': 'non-columnar'},
        {'name': 'Payment Register', 'type': 'non-columnar'},
    ]
    
    total_count = 0
    for reg in registers:
        print(f"Processing {reg['name']}...")
        rows = load_sheet_as_dicts(filename, reg['name'])
        print(f"  Found {len(rows)} entries.")
        
        for row in rows:
            try:
                date = row['Date']
                if not isinstance(date, datetime):
                    try: date = datetime.strptime(str(date), '%d-%b-%y')
                    except: continue
                
                dt_str = date.strftime('%Y-%m-%d')
                particulars = str(row['Particulars']).strip()
                vch_type = str(row.get('Vch Type') or row.get('Voucher Type'))
                vch_no = str(row.get('Vch No.') or row.get('Voucher No.'))
                
                lines = []
                
                if reg['type'] == 'columnar':
                    # Find all ledger columns
                    gross_total = float(row.get('Gross Total', 0) or 0)
                    main_acc = get_or_create_account(particulars)
                    
                    # Particulars side
                    # If it's a journal, particulars is usually Debit if Gross Total is used?
                    # Tally columnar depends on the sheet. 
                    # In Contra: Particulars is one bank. Column is another.
                    
                    # Logic for Contra
                    if reg['name'] == 'Contra Register':
                        for col_name, val in row.items():
                            if col_name in ['Date', 'Particulars', 'Voucher Type', 'Gross Total']: continue
                            if val and float(val) != 0:
                                val = float(val)
                                other_acc = get_or_create_account(col_name)
                                # Contra row: Particulars had 35000 in HDFC col.
                                # This means Particulars is credited, HDFC is debited.
                                # We'll match total.
                                lines.append((0, 0, {
                                    'account_id': other_acc.id,
                                    'debit': val if val > 0 else 0,
                                    'credit': -val if val < 0 else 0,
                                    'name': f"{vch_type} {vch_no}",
                                }))
                                lines.append((0, 0, {
                                    'account_id': main_acc.id,
                                    'debit': -val if val < 0 else 0,
                                    'credit': val if val > 0 else 0,
                                    'name': f"{vch_type} {vch_no}",
                                }))
                    
                    # Logic for Journal/Debit/Credit Notes
                    else:
                        for col_name, val in row.items():
                            if col_name in ['Date', 'Particulars', 'Voucher Type', 'Voucher No.', 'Voucher Ref. No.', 'Voucher Ref. Date', 'Value', 'Gross Total']: continue
                            if val and float(val) != 0:
                                val = float(val)
                                other_acc = get_or_create_account(col_name)
                                lines.append((0, 0, {
                                    'account_id': other_acc.id,
                                    'debit': val if val > 0 else 0,
                                    'credit': -val if val < 0 else 0,
                                    'name': f"{vch_type} {vch_no}",
                                }))
                        
                        # Balancing line
                        total_debit = sum(l[2]['debit'] for l in lines)
                        total_credit = sum(l[2]['credit'] for l in lines)
                        balance = total_debit - total_credit
                        if balance != 0:
                            lines.append((0, 0, {
                                'account_id': main_acc.id,
                                'debit': -balance if balance < 0 else 0,
                                'credit': balance if balance > 0 else 0,
                                'name': f"{vch_type} {vch_no}",
                            }))

                else: # Non-columnar (Receipt/Payment)
                    debit = float(row.get('Debit', 0) or 0)
                    credit = float(row.get('Credit', 0) or 0)
                    acc = get_or_create_account(particulars)
                    
                    if debit > 0:
                        lines.append((0, 0, {'account_id': acc.id, 'debit': debit, 'credit': 0, 'name': f"{vch_type} {vch_no}"}))
                        lines.append((0, 0, {'account_id': j_bank.default_account_id.id, 'debit': 0, 'credit': debit, 'name': f"{vch_type} {vch_no}"}))
                    elif credit > 0:
                        lines.append((0, 0, {'account_id': acc.id, 'debit': 0, 'credit': credit, 'name': f"{vch_type} {vch_no}"}))
                        lines.append((0, 0, {'account_id': j_bank.default_account_id.id, 'debit': credit, 'credit': 0, 'name': f"{vch_type} {vch_no}"}))

                if not lines: continue
                
                journal = j_bank if 'Bank' in vch_type or reg['name'] in ['Receipt Register', 'Payment Register', 'Contra Register'] else j_misc
                
                move = env['account.move'].create({
                    'move_type': 'entry',
                    'date': dt_str,
                    'ref': f"{vch_type} {vch_no}",
                    'journal_id': journal.id,
                    'line_ids': lines,
                })
                move.action_post()
                total_count += 1
                if total_count % 100 == 0:
                    env.cr.commit()
                    print(f"  ✓ Processed {total_count} records...")
            
            except Exception as e:
                print(f"Error on row: {row.get('Vch No.')}: {e}")

    env.cr.commit()
    print(f"Migration completed. Total entries: {total_count}")

migrate()
