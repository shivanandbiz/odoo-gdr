
import pandas as pd
import math
import re

FILE_PATH = '/home/biz/GDR_Original_Data/Final Data/GDR_Products_All_2026-04-20.xlsx'
df = pd.read_excel(FILE_PATH)

print("=== EXCEL DATA ANALYSIS ===")
print(f"Total Products: {len(df)}")
print(f"Unique Categories: {len(df['Category'].unique())}")
print(f"Unique Product Types in Excel: {df['Product Type'].unique()}")
print(f"Products with Qty on Hand: {len(df[df['Qty On Hand'] > 0])}")
print(f"Taxes mentioned in Excel: {df['Sales Tax'].unique()}")

# System Configuration
income_acc = env['account.account'].search([('account_type', '=', 'income')], limit=1)
expense_acc = env['account.account'].search([('account_type', '=', 'expense')], limit=1)
if not income_acc:
    income_acc = env['account.account'].search([('name', 'ilike', 'Sales')], limit=1)
if not expense_acc:
    expense_acc = env['account.account'].search([('name', 'ilike', 'Expense')], limit=1)

print(f"Using Income Account: {income_acc.name if income_acc else 'None'}")
print(f"Using Expense Account: {expense_acc.name if expense_acc else 'None'}")

# Helper for category creation
def ensure_category(full_path):
    if pd.isna(full_path) or not str(full_path).strip():
        return env.ref('product.product_category_all')
    parts = str(full_path).split('/')
    parent = None
    for part in parts:
        part = part.strip()
        if not part: continue
        cat = env['product.category'].search([('name', '=', part), ('parent_id', '=', parent.id if parent else False)], limit=1)
        if not cat:
            vals = {'name': part, 'parent_id': parent.id if parent else False}
            if income_acc: vals['property_account_income_categ_id'] = income_acc.id
            if expense_acc: vals['property_account_expense_categ_id'] = expense_acc.id
            cat = env['product.category'].create(vals)
        parent = cat
    return parent

# Tax Mapping
tax_map = {}
for tax_name in df['Sales Tax'].dropna().unique():
    # Handle multiple taxes e.g. "GST 5%, IGST 0%"
    found_ids = []
    for sub_tax in str(tax_name).split(','):
        match = re.search(r'(\d+)', sub_tax)
        if match:
            pct = float(match.group(1))
            odoo_tax = env['account.tax'].search([('amount', '=', pct), ('type_tax_use', '=', 'sale')], limit=1)
            if odoo_tax:
                found_ids.append(odoo_tax.id)
    if found_ids:
        tax_map[tax_name] = found_ids

# Purchase Tax Mapping
pur_tax_map = {}
for tax_name in df['Purchase Tax'].dropna().unique():
    found_ids = []
    for sub_tax in str(tax_name).split(','):
        match = re.search(r'(\d+)', sub_tax)
        if match:
            pct = float(match.group(1))
            odoo_tax = env['account.tax'].search([('amount', '=', pct), ('type_tax_use', '=', 'purchase')], limit=1)
            if odoo_tax:
                found_ids.append(odoo_tax.id)
    if found_ids:
        pur_tax_map[tax_name] = found_ids

print("\n=== STARTING MIGRATION ===")
created = updated = 0
for idx, row in df.iterrows():
    name = str(row['Product Name']).strip()
    if not name or name == 'nan' or name == '.': continue
    
    internal_ref = str(row['Internal Reference']).strip() if not pd.isna(row['Internal Reference']) else False
    cat_path = row['Category']
    category = ensure_category(cat_path)
    
    # Determine Type
    excel_type = str(row['Product Type']).lower()
    # Use 'consu' for physical goods (as per Odoo 17 Goods label)
    odoo_type = 'consu' if 'consu' in excel_type or 'storable' in excel_type or row['Qty On Hand'] > 0 else 'service'
    if 'service' in excel_type: odoo_type = 'service'

    vals = {
        'name': name,
        'default_code': internal_ref,
        'type': odoo_type,
        'categ_id': category.id,
        'list_price': float(row['Sales Price']) if not pd.isna(row['Sales Price']) else 0.0,
        'standard_price': float(row['Cost Price']) if not pd.isna(row['Cost Price']) else 0.0,
        'weight': float(row.get('Weight (kg)', 0)) if not pd.isna(row.get('Weight (kg)', 0)) else 0,
        'volume': float(row.get('Volume (m³)', 0)) if not pd.isna(row.get('Volume (m³)', 0)) else 0,
        'sale_ok': True,
        'purchase_ok': True,
    }
    
    # HSN Code
    hsn = str(row['HSN Code']).replace('.0', '').strip() if not pd.isna(row['HSN Code']) else False
    if hsn:
        vals['l10n_in_hsn_code'] = hsn
        
    # Taxes
    st = row.get('Sales Tax')
    if st in tax_map:
        vals['taxes_id'] = [(6, 0, tax_map[st])]
        
    pt = row.get('Purchase Tax')
    if pt in pur_tax_map:
        vals['supplier_taxes_id'] = [(6, 0, pur_tax_map[pt])]

    # Deduplication
    domain = [('name', '=', name)]
    if internal_ref:
        domain = ['|', ('default_code', '=', internal_ref)] + domain
        
    existing = env['product.template'].search(domain, limit=1)
    if existing:
        # Don't update name if it was matched by reference
        if internal_ref and existing.default_code == internal_ref:
            del vals['name']
        existing.write(vals)
        updated += 1
    else:
        env['product.template'].create(vals)
        created += 1
        
    if (created + updated) % 100 == 0:
        env.cr.commit()
        print(f"Processed {created+updated}...")

env.cr.commit()
print(f"Migration finished. Created: {created}, Updated: {updated}")
