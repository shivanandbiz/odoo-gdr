# migrate_purchase.py
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

data1 = f1[f1['Date'].dt.month.isin([4,5,6,7,8,9,10,11,12,1])]
data2 = f2[f2['Date'].dt.month.isin([2,3])]
combined = pd.concat([data1, data2], ignore_index=True)

print(f"Total records to import: {len(combined)}")

# 3. SET UP TAXES
tax_cols = {
    'SGST@ 9%': 9.0, 'CGST @ 9%': 9.0, 'IGST@18': 18.0, 
    'Cgst@2.5%': 2.5, 'Sgst@2.5%': 2.5, 'IGST@ 28': 28.0,
    'SGST@6%': 6.0, 'CGST@6%': 6.0, 'SGST@14%': 14.0, 'CGST@14%': 14.0
}

# Mapping rate name to Odoo Tax IDs to avoid redundant searches
tax_cache = {}

# 4. IMPORT PROCESS
journal = env['account.journal'].search([('type', '=', 'purchase')], limit=1)

count = 0
for idx, row in combined.iterrows():
    party_name = str(row['Particulars']).strip()
    partner = env['res.partner'].search([('name', '=', party_name)], limit=1)
    if not partner:
        partner = env['res.partner'].create({'name': party_name})
    
    taxable_val = float(row['Gross Total'])
    inv_no = str(row['Supplier Invoice No.'])
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
            'ref': inv_no if inv_no != 'nan' else f"INV/{idx}",
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
        if count % 50 == 0:
            env.cr.commit()
            print(f"  Processed {count} records...")
    except Exception as e:
        print(f"Error on row {idx}: {e}")

env.cr.commit()
print(f"Migration completed. Total imported: {count}")
