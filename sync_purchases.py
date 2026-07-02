import pandas as pd
import xmlrpc.client
import sys

def patched_init(self, colId, hidden=False, customFilters=False, method=None, val=None, **kwargs):
    self.colId, self.hidden, self.customFilters, self.method, self.val = colId, hidden, customFilters, method, val
from openpyxl.worksheet.filters import FilterColumn, CustomFilter
FilterColumn.__init__ = patched_init
CustomFilter.__init__ = patched_custom_filter_init = lambda self, operator=None, val=None, **kwargs: setattr(self, 'operator', operator) or setattr(self, 'val', val)

print("Reading Excel...")
def check_file(filename, skip):
    df = pd.read_excel(filename, sheet_name='Purchase Register', skiprows=skip)
    df = df[pd.to_datetime(df['Date'], errors='coerce').notna()]
    return df

df1 = check_file('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', 8)
df2 = check_file('/home/biz/odoo/purchase.xlsx-2025-26.......xlsx', 8)

df_all = pd.concat([df1.reset_index(drop=True), df2.reset_index(drop=True)])

# Track Excel targets
excel_targets = []
for idx, row in df_all.iterrows():
    part = str(row['Particulars']).strip()
    inv_no = str(row.get('Supplier Invoice No.', '')).strip()
    excel_amt = round(float(row.get('Gross Total', 0)), 2) if not pd.isna(row.get('Gross Total')) else 0.0
    excel_targets.append({'part': part.lower(), 'inv_no': inv_no, 'amt': excel_amt, 'matched': False})

print("Fetching Odoo invoices...")
invoices = env['account.move'].search([('move_type', '=', 'in_invoice')])
rounding_acc = env['account.account'].search([('name', 'ilike', 'round')], limit=1)

used_odoo_ids = set()

for target in excel_targets:
    best_inv = None
    best_diff = 999999999
    
    # Find best match
    for inv in invoices:
        if inv.id in used_odoo_ids: continue
        ref = inv.ref or ''
        base_ref = str(ref).split(' - ')[0].strip()
        partner = inv.partner_id.name.lower() if inv.partner_id else ''
        
        if target['inv_no'] in base_ref and target['part'] in partner:
            diff = abs(inv.amount_total - target['amt'])
            if diff < best_diff:
                best_diff = diff
                best_inv = inv
                
    if best_inv:
        used_odoo_ids.add(best_inv.id)
        target['matched'] = True
        
        diff = round(target['amt'] - best_inv.amount_total, 2)
        if diff != 0:
            was_posted = False
            if best_inv.state == 'posted':
                best_inv.button_draft()
                was_posted = True
            
            # Find existing round line
            round_line = False
            for line in best_inv.invoice_line_ids:
                if line.account_id.id == rounding_acc.id:
                    round_line = line
                    break
                    
            if round_line:
                # If negative total might happen, we need to be careful
                if best_inv.amount_total + diff < 0:
                    print(f"Warning: {best_inv.name} would be negative after diff {diff}. Skipping.")
                    continue
                round_line.price_unit += diff
            else:
                best_inv.write({'invoice_line_ids': [(0, 0, {
                    'name': 'Rounded Off',
                    'account_id': rounding_acc.id,
                    'quantity': 1,
                    'price_unit': diff,
                    'tax_ids': [(5, 0, 0)]
                })]})
                
            if was_posted:
                try:
                    best_inv.action_post()
                except Exception as e:
                    print(f"Could not post {best_inv.name}: {e}")

env.cr.commit()

# Now any Odoo invoices NOT in used_odoo_ids might be extras!
extras = [inv for inv in invoices if inv.id not in used_odoo_ids]
for ext in extras:
    print(f"Extra Odoo Invoice: {ext.name} (Ref: {ext.ref}, Part: {ext.partner_id.name}, Amt: {ext.amount_total})")
    # if ext.state == 'posted':
    #     ext.button_draft()
    # ext.unlink()

missing = [t for t in excel_targets if not t['matched']]
print(f"Total Missing: {len(missing)}")
for m in missing:
    print(f"Missing: {m}")

print("Sync completed!")
