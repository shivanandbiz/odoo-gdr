# check_purchase_totals.py
import pandas as pd
from openpyxl.worksheet.filters import FilterColumn, CustomFilter

def patched_init(self, colId, hidden=False, customFilters=False, method=None, val=None, **kwargs):
    self.colId, self.hidden, self.customFilters, self.method, self.val = colId, hidden, customFilters, method, val
FilterColumn.__init__ = patched_init

def patched_custom_filter_init(self, operator=None, val=None, **kwargs):
    self.operator = operator
    self.__dict__['val'] = val
CustomFilter.__init__ = patched_custom_filter_init


def check_file(filename, skip):
    df = pd.read_excel(filename, sheet_name='Purchase Register', skiprows=skip)
    df = df[pd.to_datetime(df['Date'], errors='coerce').notna()]
    df['Date'] = pd.to_datetime(df['Date'])
    df['Month'] = df['Date'].dt.strftime('%m-%B')
    
    # Identify the gross total column
    gross_col = 'Gross Total'
    if gross_col not in df.columns:
        print(f"Columns in {filename}: {df.columns.tolist()}")
        return None
        
    monthly = df.groupby('Month')[gross_col].sum()
    print(f"\n--- {filename} ---")
    print(monthly)
    print("GRAND TOTAL:", df[gross_col].sum())
    return df

check_file('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', 8)
check_file('/home/biz/odoo/purchase.xlsx-2025-26.......xlsx', 8)
