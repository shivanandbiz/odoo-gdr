import pandas as pd

file_path = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
sheet_name = 'Purchase Register'
try:
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl', nrows=5)
    print(f"Columns in '{sheet_name}' sheet:")
    for col in df.columns.tolist():
        print(f" - {col}")
    print("\nFirst 5 rows:")
    print(df.to_string())
except Exception as e:
    import traceback
    traceback.print_exc()
