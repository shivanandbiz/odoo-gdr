import pandas as pd

file_path = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
sheet_name = 'Purchase Register'
try:
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl', header=None, nrows=20)
    print(f"First 20 rows of '{sheet_name}' sheet (no header):")
    for idx, row in df.iterrows():
        print(f"Row {idx}: {row.tolist()}")
except Exception as e:
    import traceback
    traceback.print_exc()
