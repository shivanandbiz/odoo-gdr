import pandas as pd
from openpyxl.worksheet.filters import FilterColumn, CustomFilter

def patched_init(self, colId, hidden=False, customFilters=None, **kwargs):
    self.colId = colId
    self.hidden = hidden
    self.__dict__['customFilters'] = customFilters
FilterColumn.__init__ = patched_init

def patched_custom_filter_init(self, operator=None, val=None, **kwargs):
    self.operator = operator
    self.__dict__['val'] = val
CustomFilter.__init__ = patched_custom_filter_init

print("Fetching odoo invoices...")
invoices = env['account.move'].search([('move_type', '=', 'in_invoice')])
odoo_dict = {}
for inv in invoices:
    ref = inv.ref or ''
    base_ref = str(ref).split(' - ')[0].strip()
    partner = inv.partner_id.name if inv.partner_id else ''
    k = (partner.lower(), base_ref)
    if k not in odoo_dict:
        odoo_dict[k] = []
    odoo_dict[k].append(inv)

def check_file(filename, skip):
    df = pd.read_excel(filename, sheet_name='Purchase Register', skiprows=skip)
    df = df[pd.to_datetime(df['Date'], errors='coerce').notna()]
    return df

df1 = check_file('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', 8)
df2 = check_file('/home/biz/odoo/purchase.xlsx-2025-26.......xlsx', 8)
df_all = pd.concat([df1.reset_index(drop=True), df2.reset_index(drop=True)])

missing = []
big_diff = []

for idx, row in df_all.iterrows():
    # Only process legitimate items
    part = str(row['Particulars']).strip()
    # Handle the duplicate January or February logic?
    # We will just print ALL missing or diffs. Let's see.
    inv_no = str(row.get('Supplier Invoice No.', '')).strip()
    val = row.get('Gross Total', 0)
    if pd.isna(val) or isinstance(val, (pd.Timestamp, __import__('datetime').datetime)):
        val = 0
    try:
        excel_amt = round(float(val), 2)
    except:
        excel_amt = 0.0
    date_val = str(row['Date'])[:10]
    
    found = False
    for (o_part, o_ref), o_list in list(odoo_dict.items()):
        if inv_no in o_ref and part.lower() in o_part.lower():
            if o_list:
                found = True
                o_item = o_list.pop(0)
                diff = round(excel_amt - o_item.amount_total, 2)
                if abs(diff) > 0.01: # any diff
                    big_diff.append({'part': part, 'inv': inv_no, 'date': date_val, 'excel': excel_amt, 'odoo': o_item.amount_total, 'diff': diff})
            break
    
    if not found:
        missing.append({'part': part, 'inv': inv_no, 'date': date_val, 'excel': excel_amt})

def print_sorted(lst):
    for i, m in enumerate(sorted(lst, key=lambda x: str(x['date']))):
        print(f"{m}")
        if i > 25: 
            print("... and more")
            break

print("=== MISSING IN ODOO ===")
print_sorted(missing)
print("\n=== BIG DIFFS IN ODOO (>0.01) ===")
print_sorted([d for d in big_diff if abs(d['diff']) > 20])
print("\n=== UNMATCHED IN ODOO (Duplicates/Exces) ===")
for k, v_list in list(odoo_dict.items()):
    for inv in v_list:
        print({'part': inv.partner_id.name, 'ref': inv.ref, 'date': str(inv.date), 'amount': inv.amount_total})
