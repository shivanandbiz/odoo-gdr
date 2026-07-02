# migrate_everything_v4.py
import openpyxl
from datetime import datetime

# MONKEY-PATCH
from openpyxl.worksheet.filters import FilterColumn
def patched_init(self, colId, hidden=False, customFilters=False, method=None, val=None, **kwargs):
    self.colId, self.hidden, self.customFilters, self.method, self.val = colId, hidden, customFilters, method, val
FilterColumn.__init__ = patched_init

def get_account_type(name):
    name = name.lower().strip()
    if any(k in name for k in ['bank', 'cash', 'hdfc', 'kotak', 'indian bank']): return 'asset_cash'
    if any(k in name for k in ['receivable', 'debtors', 'railway']): return 'asset_receivable'
    if any(k in name for k in ['payable', 'creditors']): return 'liability_payable'
    if any(k in name for k in ['tax', 'gst', 'igst', 'cgst', 'sgst']): return 'asset_current'
    if any(k in name for k in ['expense', 'fees', 'salary', 'rent']): return 'expense'
    if any(k in name for k in ['income', 'sales', 'discount']): return 'income'
    if any(k in name for k in ['capital', 'equity']): return 'equity'
    if any(k in name for k in ['loan']): return 'liability_non_current'
    return 'asset_current'

def get_or_create_account(name):
    name = str(name).strip()
    if not name or name == 'None': return None
    a = env['account.account'].search([('name', '=', name)], limit=1)
    if not a:
        at = get_account_type(name)
        last = env['account.account'].search([('code', 'like', '99%')], order='code desc', limit=1)
        nc = str(int(last.code) + 1) if last else '990001'
        a = env['account.account'].create({'name': name, 'code': nc, 'account_type': at})
    return a

def parse_dt(d):
    if isinstance(d, datetime): return d
    if not d: return None
    for fmt in ('%d-%b-%y', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d-%b-%Y'):
        try: return datetime.strptime(str(d).strip(), fmt)
        except: continue
    return None

def migrate():
    fname = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
    j_misc = env['account.journal'].search([('type', '=', 'general')], limit=1)
    j_bank = env['account.journal'].search([('type', '=', 'bank')], limit=1)
    
    registers = [
        {'name': 'Contra Register', 'type': 'columnar'},
        {'name': 'Debit Note Register', 'type': 'columnar'},
        {'name': 'Journal Register', 'type': 'columnar'},
        {'name': 'Credit Note Register', 'type': 'columnar'},
        {'name': 'Receipt Register', 'type': 'non-columnar'},
        {'name': 'Payment Register', 'type': 'non-columnar'},
    ]
    
    wb = openpyxl.load_workbook(fname, read_only=True, data_only=True)
    tc = 0
    for reg in registers:
        print(f"Sheet: {reg['name']}")
        try:
            ws = wb[reg['name']]
            headers = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i == 8: headers = [str(h).strip() if h else f"Col{j}" for j,h in enumerate(row)]; continue
                if i < 10: continue
                if not any(row): continue
                p = str(row[1]).strip()
                if not p or p == 'None' or 'Total' in p or 'Grand Total' in p: continue
                dt = parse_dt(row[0])
                if not dt: continue
                ds = dt.strftime('%Y-%m-%d')
                v_type = str(row[2]).strip()
                v_no = str(row[3]).strip()
                row_data = dict(zip(headers, row))
                
                lines = []
                if reg['type'] == 'columnar':
                    m_acc = get_or_create_account(p)
                    for k,v in row_data.items():
                        if any(x in k for x in ['Date', 'Particulars', 'Voucher', 'No.', 'Ref.', 'Gross Total', 'Value']): continue
                        try:
                            fv = float(v)
                            if fv == 0: continue
                            o_acc = get_or_create_account(k)
                            if o_acc:
                                lines.append((0,0, {'account_id': o_acc.id, 'debit': fv if fv > 0 else 0, 'credit': -fv if fv < 0 else 0, 'name': f"{v_type} {v_no}"}))
                        except: continue
                    # Balance it
                    bal = sum(l[2]['debit'] for l in lines) - sum(l[2]['credit'] for l in lines)
                    if bal != 0: lines.append((0,0, {'account_id': m_acc.id, 'debit': -bal if bal <0 else 0, 'credit': bal if bal >0 else 0, 'name': f"{v_type} {v_no}"}))
                else: # Non-columnar
                    try: dr = float(row[4] or 0); cr = float(row[5] or 0)
                    except: dr, cr = 0, 0
                    a = get_or_create_account(p)
                    if dr > 0:
                        lines.append((0,0, {'account_id': a.id, 'debit': dr, 'credit': 0, 'name': f"{v_type} {v_no}"}))
                        lines.append((0,0, {'account_id': j_bank.default_account_id.id, 'debit': 0, 'credit': dr, 'name': f"{v_type} {v_no}"}))
                    elif cr > 0:
                        lines.append((0,0, {'account_id': a.id, 'debit': 0, 'credit': cr, 'name': f"{v_type} {v_no}"}))
                        lines.append((0,0, {'account_id': j_bank.default_account_id.id, 'debit': cr, 'credit': 0, 'name': f"{v_type} {v_no}"}))
                
                if not lines: continue
                move = env['account.move'].create({
                    'move_type': 'entry', 'date': ds, 'ref': f"{v_type} {v_no}",
                    'journal_id': j_bank.id if 'Bank' in v_type or reg['name'] in ['Receipt Register', 'Payment Register', 'Contra Register'] else j_misc.id,
                    'line_ids': lines,
                })
                move.action_post()
                tc += 1
                if tc % 200 == 0:
                    env.cr.commit()
                    print(f"  ✓ {tc} records...")
        except Exception as e: print(f"  ERR Sheet {reg['name']}: {e}")
            
    env.cr.commit()
    print(f"Done. Total: {tc}")

migrate()
