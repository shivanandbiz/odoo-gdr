# migrate_everything_v2.py
import openpyxl
from datetime import datetime

# MONKEY-PATCH OPENPYXL TO FIX TALLY FILTERS
from openpyxl.worksheet.filters import FilterColumn
def patched_init(self, colId, hidden=False, customFilters=False, method=None, val=None, **kwargs):
    self.colId = colId
    self.hidden = hidden
    self.customFilters = customFilters
    self.method = method
    self.val = val
FilterColumn.__init__ = patched_init

# 1. SETUP ODOO HELPERS (As before)
def get_account_type(name):
    # (Same as v1)
    name = name.lower()
    if any(k in name for k in ['bank', 'cash', 'hdfc', 'kotak', 'indian bank', 'petty']): return 'asset_cash'
    if any(k in name for k in ['gst', 'cgst', 'sgst', 'igst', 'tax']): return 'asset_current'
    if any(k in name for k in ['capital']): return 'equity'
    if any(k in name for k in ['loan']): return 'liability_non_current'
    if any(k in name for k in ['payable', 'creditors']): return 'liability_payable'
    if any(k in name for k in ['receivable', 'debtors', 'railway']): return 'asset_receivable'
    if any(k in name for k in ['expense', 'rent', 'salary']): return 'expense'
    if any(k in name for k in ['income', 'sales']): return 'income'
    return 'asset_current'

def get_or_create_account(name):
    account = env['account.account'].search([('name', '=', name)], limit=1)
    if not account:
        type_code = get_account_type(name)
        # Sequence generation for codes
        last_account = env['account.account'].search([('code', 'like', '99%')], order='code desc', limit=1)
        new_code = str(int(last_account.code) + 1) if last_account else '990001'
        account = env['account.account'].create({'name': name, 'code': new_code, 'account_type': type_code})
    return account

# 2. EXCEL LOADER (Now with robust sheet loading)
def load_sheet_as_dicts(filename, sheet_name):
    print(f"Loading {sheet_name}...")
    wb = openpyxl.load_workbook(filename, read_only=True, data_only=True)
    try:
        ws = wb[sheet_name]
        headers = []
        rows = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 8: # Row 9
                headers = [str(h).strip() if h else f"Col_{j}" for j, h in enumerate(row)]
                continue
            if i < 9: continue
            if not row or all(v is None for v in row): continue
            if row[0] and 'Total' in str(row[0]): break
            d = dict(zip(headers, row))
            rows.append(d)
        return rows
    except Exception as e:
        print(f"CRITICAL ERROR loading {sheet_name}: {e}")
        return []

# 3. MIGRATION LOGIC (Refined)
def migrate():
    filename = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
    
    j_misc = env['account.journal'].search([('type', '=', 'general')], limit=1)
    j_bank = env['account.journal'].search([('type', '=', 'bank')], limit=1) # The default bank journal
    
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
        rows = load_sheet_as_dicts(filename, reg['name'])
        if not rows: continue
        print(f"  Migrating {len(rows)} entries...")
        
        for row_data in rows:
            try:
                date = row_data.get('Date')
                if not isinstance(date, datetime): continue
                dt_str = date.strftime('%Y-%m-%d')
                
                particulars = str(row_data.get('Particulars')).strip()
                vch_type = str(row_data.get('Vch Type') or row_data.get('Voucher Type'))
                vch_no = str(row_data.get('Vch No.') or row_data.get('Voucher No.'))
                
                lines = []
                if reg['type'] == 'columnar':
                    main_acc = get_or_create_account(particulars)
                    for col_name, val in row_data.items():
                        if col_name in ['Date', 'Particulars', 'Voucher Type', 'Vch Type', 'Voucher No.', 'Vch No.', 'Voucher Ref. No.', 'Voucher Ref. Date', 'Value', 'Gross Total']: continue
                        if val is not None and str(val).strip() != '' and float(val) != 0:
                            val = float(val)
                            other_acc = get_or_create_account(col_name)
                            # Every columnar entry has a main side (Particulars) and a dynamic side (Column)
                            # Usually Tally shows Dr/Cr based on the sheet.
                            
                            # Simple rule: If it's a Contra, and the Column value is Debit...
                            # Actually, we don't know Dr/Cr for columns easily.
                            # But we know Gross Total should balance it.
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
                    debit = float(row_data.get('Debit', 0) or 0)
                    credit = float(row_data.get('Credit', 0) or 0)
                    acc = get_or_create_account(particulars)
                    
                    if debit > 0:
                        lines.append((0, 0, {'account_id': acc.id, 'debit': debit, 'credit': 0, 'name': f"{vch_type} {vch_no}"}))
                        lines.append((0, 0, {'account_id': j_bank.default_account_id.id, 'debit': 0, 'credit': debit, 'name': f"{vch_type} {vch_no}"}))
                    elif credit > 0:
                        lines.append((0, 0, {'account_id': acc.id, 'debit': 0, 'credit': credit, 'name': f"{vch_type} {vch_no}"}))
                        lines.append((0, 0, {'account_id': j_bank.default_account_id.id, 'debit': credit, 'credit': 0, 'name': f"{vch_type} {vch_no}"}))

                if not lines: continue
                
                # Check for zero-balance moves
                if abs(sum(l[2]['debit'] for l in lines) - sum(l[2]['credit'] for l in lines)) > 0.01:
                    # Forced balancing to a suspense account
                    susp_acc = get_or_create_account('Suspense Error Migration')
                    balance = sum(l[2]['debit'] for l in lines) - sum(l[2]['credit'] for l in lines)
                    lines.append((0, 0, {'account_id': susp_acc.id, 'debit': -balance if balance < 0 else 0, 'credit': balance if balance > 0 else 0, 'name': 'Balancing Line'}))

                move = env['account.move'].create({
                    'move_type': 'entry',
                    'date': dt_str,
                    'ref': f"{vch_type} {vch_no}",
                    'journal_id': j_bank.id if 'Bank' in vch_type or reg['name'] in ['Receipt Register', 'Payment Register', 'Contra Register'] else j_misc.id,
                    'line_ids': lines,
                })
                move.action_post()
                total_count += 1
                if total_count % 100 == 0:
                    env.cr.commit()
                    print(f"  ✓ Processed {total_count} records...")
                    
            except Exception as e:
                print(f"Error on voucher {vch_no}: {e}")

    env.cr.commit()
    print(f"Migration completed. Total entries: {total_count}")

migrate()
