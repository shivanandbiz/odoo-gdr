# migrate_opening_balance_v2.py
import pandas as pd
import numpy as np

def fval(v):
    try:
        if v is None or pd.isna(v): return 0.0
        return float(str(v).replace(',',''))
    except: return 0.0

def migrate():
    print("Reading Balance Sheet (2) for Leaf Accounts...")
    df = pd.read_excel('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', sheet_name='Balance Sheet (2)', header=None)
    
    # ── 1. DEFINING LEAF ACCOUNTS ─────────────────────────────────────────────
    liab_leaves = [
        ('Capital Account', 3279120.0),
        ('Secured Loans', -3238902.54),
        ('Unsecured Loans', 125035627.50),
        ('DEFFERED TAX LIABILITY', -101048.0),
        ('Electronica Finance Limited', -662035.0),
        ('Duties & Taxes', -4525832.25),
        ('Provisions', 537889.0),
        ('Sundry Creditors', 86700338.49),
        ('Contract Sal Payble A/c', -2000.0),
        ('Daily Wages Payble A/c', 11906.0),
        ('director remunaration payable to Jawahar Krishna', 300000.0),
        ('Electricity Charges Payable', -309900.62),
        ('EPFO- Administation Payable', -19372.0),
        ('EPFO- Employees Share', 16392.0),
        ('EPFO -Employers Share', -168366.0),
        ('LABOUR WELFARE FUND Payable', -1396.0),
        ('Raja M Sal', 360.0),
        ('Rekha Food Expenses', 18750.0),
        ('Rent Payable Hp', 7500.0),
        ('Stipend Payable', 141727.0),
        ('Profit & Loss A/c', 66962.74),
    ]
    
    asset_leaves = [
        ('COMPUTER', 163559.0),
        ('FURNITURE & FIXTURE', 405278.0),
        ('Vehicles', 7740608.0),
        ('Capital Work-in-Progress', 441850.0),
        ('Interior Works', 4575.0),
        ('Mobile', 45080.28),
        ('Office Equipment', 82395.51),
        ('Plant and Machinery', 94471063.0),
        ('Plant & Machinery', 304900.0),
        ('Renewable Energy Assets (Solar Plant)', 6000000.0),
        ('Software', 353067.47),
        ('Closing Stock', 25525210.0),
        ('Deposits (Asset)', 12646749.14),
        ('Loans & Advances (Asset)', 9834061.91),
        ('Sundry Debtors', 60773774.40),
        ('Cash-in-hand', 316429.0),
        ('Bank Accounts', -27636683.53),
        ('Employee Exp Advance', 13174.88),
        ('Salary Advances', 7000.0),
        ('Licence Fee Paid to ESCORTS LTD', 3600000.0),
        ('Suspense', 3253423.31),
        ('tcs receivable', 101831.0),
        ('Tds on Fd', 97174.0),
        ('TDS Rececivable', 199555.05),
    ]

    def get_acc(name, side):
        lname = name.lower()
        atype = 'asset_current'
        if side == 'credit': atype = 'liability_current'
        if 'capital' in lname or 'equity' in lname: atype = 'equity'
        if 'profit & loss' in lname: atype = 'equity_unaffected'
        if 'tax' in lname: atype = 'liability_current'
        if 'creditor' in lname: atype = 'liability_payable'
        if 'debtor' in lname: atype = 'asset_receivable'
        if 'bank' in lname or 'cash' in lname: atype = 'asset_cash'
        if any(x in lname for x in ['fixed','computer','machinery','furniture','vehicle','interior','software','mobile','equipment','solar','work-in-progress']):
            atype = 'asset_fixed'

        acc = env['account.account'].search([('name', '=', name)], limit=1)
        if not acc:
            # Clean code: Alphanumeric and dots only
            clean_code = "".join(filter(str.isalnum, name[:10]))
            code = f"OB.{clean_code}"
            # Ensure uniqueness
            idx = 1
            while env['account.account'].search_count([('code', '=', code)]):
                code = f"OB.{clean_code}.{idx}"
                idx += 1
            acc = env['account.account'].create({'name': name, 'code': code, 'account_type': atype})
        else:
            if acc.account_type != atype and acc.account_type not in ('asset_cash', 'asset_receivable', 'liability_payable'):
                acc.account_type = atype
        return acc

    lines = []
    for name, amt in liab_leaves:
        acc = get_acc(name, 'credit')
        if amt > 0: lines.append((acc.id, 0.0, amt))
        else: lines.append((acc.id, abs(amt), 0.0))
    for name, amt in asset_leaves:
        acc = get_acc(name, 'debit')
        if amt > 0: lines.append((acc.id, amt, 0.0))
        else: lines.append((acc.id, 0.0, abs(amt)))

    total_deb = sum(l[1] for l in lines)
    total_cre = sum(l[2] for l in lines)
    diff = total_deb - total_cre
    if abs(diff) > 0.01:
        suspense = get_acc('Difference in Opening Balance', 'credit')
        if diff > 0: lines.append((suspense.id, 0.0, diff))
        else: lines.append((suspense.id, abs(diff), 0.0))

    env['account.move'].search([('date', '=', '2025-04-01'), ('ref', 'ilike', 'Opening')]).button_draft()
    env['account.move'].search([('date', '=', '2025-04-01'), ('ref', 'ilike', 'Opening')]).unlink()

    journal = env['account.journal'].search([('type', '=', 'general')], limit=1)
    move = env['account.move'].create({
        'ref': 'Opening Balance 2025-26 (Final Match)',
        'date': '2025-04-01',
        'journal_id': journal.id,
        'line_ids': [(0, 0, {
            'account_id': lid,
            'debit': d, 'credit': c,
            'name': 'Opening Balance'
        }) for lid, d, c in lines]
    })
    move.action_post()
    env.cr.commit()
    print(f"Posted opening balance for {len(lines)} accounts.")
    print(f"Total Debit/Credit: {move.amount_total:,.2f}")

migrate()
