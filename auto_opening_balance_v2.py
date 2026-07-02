# auto_opening_balance_v2.py
import pandas as pd

# Load Excel
df = pd.read_excel('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', sheet_name='Balance Sheet (2)')
data = df.iloc[8:].reset_index(drop=True)

# Find Accounts
acc_map = {
    'Fixed Assets': env['account.account'].search([('code', '=', '151000')], limit=1),
    'Stock': env['account.account'].search([('code', '=', '110100')], limit=1),
    'Current Assets': env['account.account'].search([('code', '=', '101000')], limit=1),
    'Receivable': env['account.account'].search([('code', '=', '121000')], limit=1),
    'Bank': env['account.account'].search([('code', '=', '101401')], limit=1),
    'Tax Receivable': env['account.account'].search([('code', '=', '132000')], limit=1),
    'Capital': env['account.account'].search([('code', '=', '301000')], limit=1),
    'Loan': env['account.account'].search([('code', '=', '291000')], limit=1),
    'Payable': env['account.account'].search([('code', '=', '211000')], limit=1),
    'Current Liabilities': env['account.account'].search([('code', '=', '201000')], limit=1),
    'Salary': env['account.account'].search([('code', '=', '230000')], limit=1),
    'Tax Payable': env['account.account'].search([('code', '=', '252000')], limit=1),
    'Retained': env['account.account'].search([('code', '=', '999999')], limit=1),
}

journal = env['account.journal'].search([('code', '=', 'MISC')], limit=1)

def get_odoo_account(tally_name, current_group, side):
    name = str(tally_name).lower()
    if 'capital' in name: return acc_map['Capital']
    if 'creditors' in name: return acc_map['Payable']
    if 'debtors' in name: return acc_map['Receivable']
    if 'bank' in name or 'cash' in name: return acc_map['Bank']
    if 'stock' in name: return acc_map['Stock']
    if 'fixed assets' in name or current_group == 'Fixed Assets': return acc_map['Fixed Assets']
    if 'loan' in name: return acc_map['Loan']
    if 'tax' in name or 'tds' in name or 'tcs' in name: 
        if 'receivable' in name or 'asset' in str(current_group).lower(): return acc_map['Tax Receivable']
        return acc_map['Tax Payable']
    if 'salary' in name or 'wage' in name or 'remunaration' in name or 'payble' in name or 'stipend' in name or 'epfo' in name: return acc_map['Salary']
    if 'profit' in name or 'difference' in name: return acc_map['Retained']
    
    # Side-based fallbacks
    if side == 'asset':
        if current_group == 'Fixed Assets': return acc_map['Fixed Assets']
        return acc_map['Current Assets']
    else:
        return acc_map['Current Liabilities']

# Aggregate balances by account to follow the "No multiple lines for 999999" and "Proper separation" rules
account_balances = {} # {account_id: {'debit': X, 'credit': Y, 'names': [n1, n2...]}}

def record_balance(acc, name, debit, credit):
    if debit == 0 and credit == 0: return
    if acc.id not in account_balances:
        account_balances[acc.id] = {'debit': 0, 'credit': 0, 'names': []}
    account_balances[acc.id]['debit'] += debit
    account_balances[acc.id]['credit'] += credit
    account_balances[acc.id]['names'].append(name)

current_group_liab = None
current_group_asset = None

for index, row in data.iterrows():
    # Left Side (Liabilities)
    l_name = row.iloc[0]
    l_val = row.iloc[2]
    if not pd.isna(l_name) and str(l_name) != 'Total':
        if pd.isna(l_val): current_group_liab = l_name
        else:
            acc = get_odoo_account(l_name, current_group_liab, 'liability')
            val = float(l_val)
            if val > 0: record_balance(acc, l_name, 0, val)
            elif val < 0: record_balance(acc, l_name, abs(val), 0)

    # Right Side (Assets)
    r_name = row.iloc[3]
    r_val = row.iloc[5]
    if not pd.isna(r_name) and str(r_name) != 'Total':
        if pd.isna(r_val): current_group_asset = r_name
        else:
            acc = get_odoo_account(r_name, current_group_asset, 'asset')
            val = float(r_val)
            if val > 0: record_balance(acc, r_name, val, 0)
            elif val < 0: record_balance(acc, r_name, 0, abs(val))

# Prepare lines (COMBINING 999999)
lines = []
for acc_id, balance in account_balances.items():
    # Force aggregation for 999999 or others if requested
    final_debit = balance['debit']
    final_credit = balance['credit']
    
    # Netting off for each account
    if final_debit > final_credit:
        final_debit -= final_credit
        final_credit = 0
    else:
        final_credit -= final_debit
        final_debit = 0
    
    if final_debit > 0 or final_credit > 0:
        lines.append((0, 0, {
            'account_id': acc_id,
            'name': f"Opening: {', '.join(balance['names'][:5])}..." if len(balance['names']) > 1 else f"Opening: {balance['names'][0]}",
            'debit': final_debit,
            'credit': final_credit,
        }))

# Cleanup old entry
env['account.move'].search([('ref', '=', 'Opening Balance FY 2025-26 (Proper)')]).button_draft()
env['account.move'].search([('ref', '=', 'Opening Balance FY 2025-26 (Proper)')]).unlink()

# Create Move
move = env['account.move'].create({
    'move_type': 'entry',
    'date': '2025-04-01',
    'journal_id': journal.id,
    'ref': 'Opening Balance FY 2025-26 (Proper)',
    'line_ids': lines,
})

# Post
move.action_post()
env.cr.commit()
print(f"  ✅ Corrected Opening Balance entry created: {move.name}")
print(f"  Total Debits: {sum(l[2]['debit'] for l in lines)}")
print(f"  Total Credits: {sum(l[2]['credit'] for l in lines)}")
print(f"  Account 999999 used {len([l for l in lines if l[2]['account_id'] == acc_map['Retained'].id])} times.")
