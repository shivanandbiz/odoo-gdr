import pandas as pd
import sys

files = [
    '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx',
    '/home/biz/odoo/purchase.xlsx-2025-26.......xlsx'
]

for file in files:
    try:
        # We need to find the sheet that corresponds to purchases
        xl = pd.ExcelFile(file)
        print(f"File: {file}")
        print(f"Sheets: {xl.sheet_names}")
    except Exception as e:
        print(f"Error reading {file}: {e}")
