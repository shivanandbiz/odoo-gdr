# migrate_purchase_v3.py
import pandas as pd
from datetime import datetime

# 1. CLEAN EXISTING BILLS
print("Cleaning existing bills...")
moves = env['account.move'].search([('move_type', '=', 'in_invoice')])
if moves:
    moves.button_draft()
    moves.unlink()
    env.cr.commit()
    print(f"  ✓ Deleted bills.")

# 2. COLLECT RECORDS
def get_df(filename, skip):
    df = pd.read_excel(filename, sheet_name='Purchase Register', skiprows=skip)
    df.columns = df.columns.str.strip()
    df = df[pd.to_datetime(df['Date'], errors='coerce').notna()]
    df['Date'] = pd.to_datetime(df['Date'])
    df['Gross Total'] = pd.to_numeric(df['Gross Total'], errors='coerce').fillna(0)
    return df

f1 = get_df('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', 8)
f2 = get_df('/home/biz/odoo/purchase.xlsx-2025-26.......xlsx', 8)

data_apr_dec = f1[(f1.index < 824) & (f1['Date'].dt.year == 2025)]
data_jan = f1[(f1.index >= 824) & (f1['Date'].dt.month == 1) & (f1['Date'].dt.year == 2026)]
data_feb_mar = f2[f2['Date'].dt.month.isin([2, 3]) & (f2['Date'].dt.year == 2026)]

combined = pd.concat([data_apr_dec, data_jan, data_feb_mar], ignore_index=True)
print(f"Total verified records to import: {len(combined)}")

# 3. SET UP TAXES
# Since Odoo only has '18%', we will map all GST logic to relevant Rates.
# If a rate (like 12% or 5%) doesn't exist, we will create it to 'display' correctly.
def get_or_create_tax(name, amount):
    tax = env['account.tax'].search([('amount', '=', amount), ('type_tax_use', '=', 'purchase')], limit=1)
    if not tax:
        tax = env['account.tax'].create({
            'name': name,
            'amount': amount,
            'type_tax_use': 'purchase',
            'amount_type': 'percent'
        })
    return tax.id

tax_cols = {
    'SGST@ 9%': 18.0, 'CGST @ 9%': 18.0, 'IGST@18': 18.0, 
    'Cgst@2.5%': 5.0, 'Sgst@2.5%': 5.0, 'IGST@ 28': 28.0,
    'SGST@6%': 12.0, 'CGST@6%': 12.0, 'SGST@14%': 28.0, 'CGST@14%': 28.0
}

journal = env['account.journal'].search([('type', '=', 'purchase')], limit=1)

count = 0
for idx, row in combined.iterrows():
    party_name = str(row['Particulars']).strip()
    partner = env['res.partner'].search([('name', '=', party_name)], limit=1)
    if not partner:
        partner = env['res.partner'].create({'name': party_name})
    
    taxable_val = float(row['Gross Total'])
    inv_no = str(row['Supplier Invoice No.'])
    if taxable_val == 0 and inv_no == 'nan': continue
    
    dt = row['Date'].strftime('%Y-%m-%d')
    
    # Tax detection
    tax_rate = 0
    for col, rate in tax_cols.items():
        if col in combined.columns:
            val = pd.to_numeric(row[col], errors='coerce')
            if pd.notna(val) and val > 0:
                tax_rate = max(tax_rate, rate)
    
    applied_taxes = []
    if tax_rate > 0:
        tax_name = f"GST {int(tax_rate)}%"
        applied_taxes = [get_or_create_tax(tax_name, tax_rate)]

    try:
        move = env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': dt,
            'date': dt,
            'ref': inv_no if inv_no != 'nan' else f"INV/MIG/{idx}",
            'journal_id': journal.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Purchase (Migration)',
                'quantity': 1,
                'price_unit': taxable_val,
                'tax_ids': [(6, 0, applied_taxes)],
            })],
        })
        move.action_post()
        count += 1
        if count % 100 == 0:
            env.cr.commit()
            print(f"  ✓ Processed {count} records...")
    except Exception as e:
        print(f"Error row {idx}: {e}")

env.cr.commit()
print(f"Migration completed. Total imported: {count}")
