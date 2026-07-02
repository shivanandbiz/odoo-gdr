# analyze_purchase.py
import pandas as pd
from openpyxl.worksheet.filters import FilterColumn, CustomFilter

def patched_init(self, colId, hidden=False, customFilters=False, method=None, val=None, **kwargs):
    self.colId, self.hidden, self.customFilters, self.method, self.val = colId, hidden, customFilters, method, val
FilterColumn.__init__ = patched_init

def patched_custom_filter_init(self, operator=None, val=None, **kwargs):
    self.operator = operator
    self.__dict__['val'] = val
CustomFilter.__init__ = patched_custom_filter_init


def analyze_file(filename, sheetname):
    print(f"\n--- Analyzing {filename} [{sheetname}] ---")
    df = pd.read_excel(filename, sheet_name=sheetname)
    print("Columns:", df.columns.tolist())
    
    # Try to find Date and Amount columns
    date_col = next((c for c in df.columns if 'Date' in str(c)), None)
    total_col = next((c for c in df.columns if 'Total' in str(c) or 'Gross' in str(c) or 'Amount' in str(c)), None)
    vouch_no_col = next((c for c in df.columns if 'Voucher' in str(c) or 'No' in str(c)), None)
    party_name_col = next((c for c in df.columns if 'Particulars' in str(c) or 'Party' in str(c) or 'Supplier' in str(c)), None)

    print(f"Detected columns: Date='{date_col}', Amount='{total_col}', VoucherNo='{vouch_no_col}'")
    if not date_col or not total_col:
        print("Required columns not found")
        return None

    # Clean data
    df = df[pd.notna(df[date_col]) & pd.notna(df[total_col])]
    # Remove 'Total' row
    df = df[~df[date_col].astype(str).str.contains('Total', case=False, na=False)]
    
    # Convert to datetime
    df['DateProcessed'] = pd.to_datetime(df[date_col], errors='coerce')
    df = df[pd.notna(df['DateProcessed'])]
    
    # Categorize by Month
    df['Month'] = df['DateProcessed'].dt.month_name()
    monthly_totals = df.groupby(df['DateProcessed'].dt.strftime('%m-%B')).agg({total_col: 'sum'})
    print(monthly_totals)
    print("Grand Total:", df[total_col].sum())
    return df

analyze_file('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', 'Purchase Register')
analyze_file('/home/biz/odoo/purchase.xlsx-2025-26.......xlsx', 'Purchase Register')
