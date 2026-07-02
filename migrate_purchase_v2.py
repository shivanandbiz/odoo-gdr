# migrate_purchase_v2.py
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

# SOURCE logic refined based on segment analysis:
# File 1 has a "Bad Jan" at the top (indices 0 to somewhere before 824).
# Tally match Jan starts at index 824 in File 1.
# April-Dec 2025 are only in index < 824.
# Feb-Mar 2026 are primarily in File 2.

# Filtering File 1 correctly:
# 1. All records for Apr-Dec 2025 (these are in the first segment)
data_apr_dec = f1[(f1.index < 824) & (f1['Date'].dt.year == 2025)]
# 2. January 2026 records only from second segment (index >= 824)
data_jan = f1[(f1.index >= 824) & (f1['Date'].dt.month == 1) & (f1['Date'].dt.year == 2026)]

# Adding File 2: February-March 2026
data_feb_mar = f2[f2['Date'].dt.month.isin([2, 3]) & (f2['Date'].dt.year == 2026)]

combined = pd.concat([data_apr_dec, data_jan, data_feb_mar], ignore_index=True)

print(f"Total verified records to import: {len(combined)}")

# 3. SET UP TAXES AND PARTNERS
tax_cols = {
    'SGST@ 9%': 9.0, 'CGST @ 9%': 9.0, 'IGST@18': 18.0, 
    'Cgst@2.5%': 2.5, 'Sgst@2.5%': 2.5, 'IGST@ 28': 28.0,
    'SGST@6%': 6.0, 'CGST@6%': 6.0, 'SGST@14%': 14.0, 'CGST@14%': 14.0
}
tax_cache = {}
journal = env['account.journal'].search([('type', '=', 'purchase')], limit=1)

count = 0
for idx, row in combined.iterrows():
    party_name = str(row['Particulars']).strip()
    partner = env['res.partner'].search([('name', '=', party_name)], limit=1)
    if not partner:
        partner = env['res.partner'].create({'name': party_name})
    
    taxable_val = float(row['Gross Total'])
    inv_no = str(row['Supplier Invoice No.'])
    # Skip potential duplicates or empty headers if any remain
    if taxable_val == 0 and inv_no == 'nan': continue
    
    dt = row['Date'].strftime('%Y-%m-%d')
    applied_taxes = []
    for col, rate in tax_cols.items():
        if col in combined.columns:
            val = pd.to_numeric(row[col], errors='coerce')
            if pd.notna(val) and val > 0:
                tax_type = 'SGST' if 'SGST' in col.upper() else 'CGST' if 'CGST' in col.upper() else 'IGST'
                cache_key = (tax_type, rate)
                if cache_key not in tax_cache:
                    tax = env['account.tax'].search([('name', 'ilike', tax_type), ('amount', '=', rate), ('type_tax_use', '=', 'purchase')], limit=1)
                    tax_cache[cache_key] = tax.id if tax else None
                if tax_cache[cache_key]:
                    applied_taxes.append(tax_cache[cache_key])
    
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
