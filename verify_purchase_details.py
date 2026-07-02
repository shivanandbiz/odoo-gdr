import pandas as pd
from openpyxl.worksheet.filters import FilterColumn, CustomFilter

def patched_init(self, colId, hidden=False, customFilters=False, method=None, val=None, **kwargs):
    self.colId, self.hidden, self.customFilters, self.method, self.val = colId, hidden, customFilters, method, val
FilterColumn.__init__ = patched_init

def patched_custom_filter_init(self, operator=None, val=None, **kwargs):
    self.operator = operator
    self.__dict__['val'] = val
CustomFilter.__init__ = patched_custom_filter_init

import xmlrpc.client
db = 'Odoo'
url = 'http://localhost:8069'
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, 'admin', 'admin', {})

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def get_odoo_invoices():
    # Fetch all posted purchase invoices
    invoices = models.execute_kw(db, uid, 'admin', 'account.move', 'search_read',
        [[('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]],
        {'fields': ['name', 'ref', 'partner_id', 'amount_total', 'date']})
    return invoices

odoo_invs = get_odoo_invoices()
# Create index of odoo invoices by partner name and ref/invoice number
# Tally might not set 'ref' exactly as Invoice NO. It might set 'ref' to Invoice NO. + suffix in case of duplicates?
# Or maybe the name of the invoice is used.

# Let's just track all Odoo invoices
odoo_dict = {}
for inv in odoo_invs:
    ref = inv['ref'] or ''
    # Some scripts put suffix like "Inv - (1)"
    base_ref = str(ref).split(' - ')[0].strip()
    partner = inv['partner_id'][1] if inv['partner_id'] else ''
    amt = inv['amount_total']
    odoo_dict[(partner.lower(), base_ref)] = amt

def check_file(filename, skip):
    df = pd.read_excel(filename, sheet_name='Purchase Register', skiprows=skip)
    df = df[pd.to_datetime(df['Date'], errors='coerce').notna()]
    return df

df1 = check_file('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', 8)
df2 = check_file('/home/biz/odoo/purchase.xlsx-2025-26.......xlsx', 8)

df_all = pd.concat([df1.reset_index(drop=True), df2.reset_index(drop=True)])
df_all['Date'] = pd.to_datetime(df_all['Date'])
df_all['Month'] = df_all['Date'].dt.strftime('%m-%B')

# Filter for valid dates based on requirements (e.g. up to March 2026?)
df_all = df_all[df_all['Month'] != '01-January'] # Wait, Jan is in df1, but we need to see what's actually there.

print(f"Total excel rows: {len(df_all)}")
# Compare matching logic: Odoo might have modified names. Let's just print top mismatches.
# Actually, the simplest check is to find missing ones or mismatched amounts.

missing = []
mismatch = []

for idx, row in df_all.iterrows():
    part = str(row['Particulars']).strip()
    inv_no = str(row.get('Supplier Invoice No.', '')).strip()
    
    excel_amt = round(float(row['Gross Total']), 2) if not pd.isna(row['Gross Total']) else 0.0
    
    # Try finding in Odoo
    found = False
    for (o_part, o_ref), o_amt in list(odoo_dict.items()):
        if inv_no in o_ref and part.lower() in o_part.lower():
            found = True
            if abs(o_amt - excel_amt) > 0.01:
                mismatch.append({'part': part, 'inv_no': inv_no, 'excel': excel_amt, 'odoo': o_amt})
            # Removing matched so we can find duplicates if any
            del odoo_dict[(o_part, o_ref)] 
            break
    
    if not found:
        missing.append({'part': part, 'inv_no': inv_no, 'excel': excel_amt})

print(f"Mismatches: {len(mismatch)}")
for m in mismatch[:10]:
    print(m)

print(f"Missing: {len(missing)}")
for m in missing[:10]:
    print(m)

