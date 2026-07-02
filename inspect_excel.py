import pandas as pd

file_path = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
try:
    xl = pd.ExcelFile(file_path)
    print(f"Sheets: {xl.sheet_names}")
    for sheet in xl.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet, nrows=5)
        print(f"\nSheet: {sheet}")
        print(df.columns.tolist())
        print(df.head())
except Exception as e:
    print(f"Error: {e}")
