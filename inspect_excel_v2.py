import pandas as pd

file_path = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
try:
    for sheet in ['All Vouchers', 'Day Book']:
        print(f"\n--- Sheet: {sheet} ---")
        df = pd.read_excel(file_path, sheet_name=sheet, skiprows=8, nrows=10)
        print(df.columns.tolist())
        print(df)
except Exception as e:
    print(f"Error: {e}")
