# migrate_purchase_v4.py
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

# 3. SET UP TAXES (Specific GST Breakdown)
def get_tax(name, amount):
    # Search by exact name to ensure 'GST 18%' or 'IGST 18%' displays
    tax = env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', 'purchase')], limit=1)
    if not tax:
        tax = env['account.tax'].create({
            'name': name,
            'amount': amount,
            'type_tax_use': 'purchase',
            'amount_type': 'percent'
        })
    return tax.id

journal = env['account.journal'].search([('type', '=', 'purchase')], limit=1)

count = 0
for idx, row in combined.iterrows():
    party_name = str(row['Particulars']).strip()
    partner = env['res.partner'].search([('name', '=', party_name)], limit=1)
    if not partner: partner = env['res.partner'].create({'name': party_name})
    
    taxable_val = float(row['Gross Total'])
    inv_no = str(row['Supplier Invoice No.'])
    if taxable_val == 0 and inv_no == 'nan': continue
    
    dt = row['Date'].strftime('%Y-%m-%d')
    
    # Detect GST Type
    applied_taxes = []
    
    # IGST check
    if 'IGST@18' in combined.columns and pd.to_numeric(row['IGST@18'], errors='coerce') > 0:
        applied_taxes.append(get_tax('IGST 18%', 18.0))
    elif 'IGST@ 28' in combined.columns and pd.to_numeric(row['IGST@ 28'], errors='coerce') > 0:
        applied_taxes.append(get_tax('IGST 28%', 28.0))
    # Local GST check (CGST + SGST)
    elif 'CGST @ 9%' in combined.columns and pd.to_numeric(row['CGST @ 9%'], errors='coerce') > 0:
        applied_taxes.append(get_tax('CGST 9%', 9.0))
        applied_taxes.append(get_tax('SGST 9%', 9.0))
    elif 'CGST@6%' in combined.columns and pd.to_numeric(row['CGST@6%'], errors='coerce') > 0:
        applied_taxes.append(get_tax('CGST 6%', 6.0))
        applied_taxes.append(get_tax('SGST 6%', 6.0))
    elif 'Cgst@2.5%' in combined.columns and pd.to_numeric(row['Cgst@2.5%'], errors='coerce') > 0:
        applied_taxes.append(get_tax('CGST 2.5%', 2.5))
        applied_taxes.append(get_tax('SGST 2.5%', 2.5))
    elif 'CGST@14%' in combined.columns and pd.to_numeric(row['CGST@14%'], errors='coerce') > 0:
        applied_taxes.append(get_tax('CGST 14%', 14.0))
        applied_taxes.append(get_tax('SGST 14%', 14.0))
    # Fallback to generic 18% if no specific column matched but total seems 18%
    else:
        applied_taxes = [get_tax('GST 18%', 18.0)]

    try:
        move = env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': dt, 'date': dt,
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
