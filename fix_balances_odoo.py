import pandas as pd
from openpyxl.worksheet.filters import FilterColumn, CustomFilter

def patched_init(self, colId, hidden=False, customFilters=False, method=None, val=None, **kwargs):
    self.colId, self.hidden, self.customFilters, self.method, self.val = colId, hidden, customFilters, method, val
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

print("Reading excel...")
df1 = check_file('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', 8)
df2 = check_file('/home/biz/odoo/purchase.xlsx-2025-26.......xlsx', 8)

df_all = pd.concat([df1.reset_index(drop=True), df2.reset_index(drop=True)])

to_fix = []
missing = []

print("Comparing...")

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
                o_amt = o_item.amount_total
                diff = round(excel_amt - o_amt, 2)
                if abs(diff) > 0.01 and abs(diff) < 20.0:
                    to_fix.append({'inv': o_item, 'diff': diff, 'state': o_item.state})
            break

rounding_acc = env['account.account'].search([('name', 'ilike', 'round')], limit=1)

for f in to_fix:
    inv = f['inv']
    diff = f['diff']
    
    was_posted = False
    if inv.state == 'posted':
        inv.button_draft()
        was_posted = True
    
    # Check if a rounding line already exists
    rounding_line = None
    for line in inv.invoice_line_ids:
        if line.account_id.id == rounding_acc.id:
            rounding_line = line
            break
            
    if rounding_line:
        rounding_line.price_unit += diff
    else:
        inv.write({
            'invoice_line_ids': [(0, 0, {
                'name': 'Rounded Off',
                'account_id': rounding_acc.id,
                'quantity': 1,
                'price_unit': diff,
                'tax_ids': [(5, 0, 0)]
            })]
        })
        
    if was_posted:
        inv.action_post()

env.cr.commit()
print(f"Fixed {len(to_fix)} rounding errors.")
