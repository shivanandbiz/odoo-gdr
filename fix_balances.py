import pandas as pd
from openpyxl.worksheet.filters import FilterColumn, CustomFilter
import xmlrpc.client
import sys

def patched_init(self, colId, hidden=False, customFilters=False, method=None, val=None, **kwargs):
    self.colId, self.hidden, self.customFilters, self.method, self.val = colId, hidden, customFilters, method, val
FilterColumn.__init__ = patched_init

def patched_custom_filter_init(self, operator=None, val=None, **kwargs):
    self.operator = operator
    self.__dict__['val'] = val
CustomFilter.__init__ = patched_custom_filter_init

db = 'Odoo'
url = 'http://localhost:8069'
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, 'admin', 'admin', {})

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("Fetching odoo invoices...")
# Fetch all purchase invoices
invoices = models.execute_kw(db, uid, 'admin', 'account.move', 'search_read',
    [[('move_type', '=', 'in_invoice')]],
    {'fields': ['name', 'ref', 'partner_id', 'amount_total', 'state']})

odoo_dict = {}
for inv in invoices:
    ref = inv['ref'] or ''
    # Match how we did the original importing
    base_ref = str(ref).split(' - ')[0].strip()
    partner = inv['partner_id'][1] if inv['partner_id'] else ''
    k = (partner.lower(), base_ref)
    if k not in odoo_dict:
        odoo_dict[k] = []
    odoo_dict[k].append(inv)

def check_file(filename, skip):
    df = pd.read_excel(filename, sheet_name='Purchase Register', skiprows=skip)
    df = df[pd.to_datetime(df['Date'], errors='coerce').notna()]
    return df

print("Reading excel...")
df1 = check_file('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', 8)
df2 = check_file('/home/biz/odoo/purchase.xlsx-2025-26.......xlsx', 8)

df_all = pd.concat([df1.reset_index(drop=True), df2.reset_index(drop=True)])

to_fix = []
missing = []

print("Comparing...")
import collections
missing_map = collections.defaultdict(list)

for idx, row in df_all.iterrows():
    part = str(row['Particulars']).strip()
    inv_no = str(row.get('Supplier Invoice No.', '')).strip()
    excel_amt = round(float(row['Gross Total']), 2) if not pd.isna(row['Gross Total']) else 0.0
    
    found = False
    for (o_part, o_ref), o_list in list(odoo_dict.items()):
        if inv_no in o_ref and part.lower() in o_part.lower():
            if o_list:
                found = True
                o_item = o_list.pop(0)
                o_amt = o_item['amount_total']
                o_id = o_item['id']
                diff = round(excel_amt - o_amt, 2)
                # Ensure the diff is just a rounding error
                if abs(diff) > 0.01 and abs(diff) < 20.0:
                    to_fix.append({'id': o_id, 'diff': diff, 'state': o_item['state'], 'name': o_item['name']})
            break
    
    if not found:
        missing.append({'part': part, 'inv_no': inv_no, 'excel': excel_amt})

print(f"Missing in target: {len(missing)}")
print(f"To fix rounding errors: {len(to_fix)}")

# Fix missing: some might just have completely broken refs.
rounding_acc_id = 470 

for f in to_fix:
    m_id = f['id']
    diff = f['diff']
    print(f"Fixing {f['name']} with diff {diff}")
    
    # 1. Draft
    if f['state'] == 'posted':
        models.execute_kw(db, uid, 'admin', 'account.move', 'button_draft', [[m_id]])
    
    # 2. Add rounding line
    models.execute_kw(db, uid, 'admin', 'account.move', 'write', [[m_id], {
        'invoice_line_ids': [(0, 0, {
            'name': 'Rounded Off',
            'account_id': rounding_acc_id,
            'quantity': 1,
            'price_unit': diff,
            'tax_ids': [(5, 0, 0)] # Remove default taxes
        })]
    }])
    
    # 3. Post
    if f['state'] == 'posted':
        models.execute_kw(db, uid, 'admin', 'account.move', 'action_post', [[m_id]])

print("Done fixing balances.")
