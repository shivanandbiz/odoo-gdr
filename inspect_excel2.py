import pandas as pd

file_path = '/home/biz/odoo/oddo_products.xlsx'
df = pd.read_excel(file_path, engine='openpyxl')

print(f"Total rows: {len(df)}")
print(f"Total columns: {len(df.columns)}")
print("\n=== ALL COLUMN NAMES ===")
for i, col in enumerate(df.columns):
    print(f"  [{i}] {col}")

# Show a few key columns to understand data
key_cols = [c for c in df.columns if c in [
    'id', 'name', 'default_code', 'list_price', 'standard_price',
    'type', 'categ_id', 'uom_id', 'uom_po_id', 'description',
    'sale_ok', 'purchase_ok', 'taxes_id', 'supplier_taxes_id',
    'barcode', 'weight', 'volume'
]]

print(f"\n=== KEY COLUMNS FOUND ===")
print(key_cols)
print("\n=== SAMPLE DATA (key columns, first 5 rows) ===")
if key_cols:
    print(df[key_cols].head(5).to_string())

print(f"\n=== NON-NULL COUNT PER COLUMN (top 30) ===")
non_null = df.notna().sum().sort_values(ascending=False).head(30)
print(non_null)
