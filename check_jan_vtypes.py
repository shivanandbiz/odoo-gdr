import pandas as pd
from openpyxl.worksheet.filters import FilterColumn, CustomFilter

def patched_init(self, colId, hidden=False, customFilters=False, method=None, val=None, **kwargs):
    self.colId, self.hidden, self.customFilters, self.method, self.val = colId, hidden, customFilters, method, val
FilterColumn.__init__ = patched_init

def patched_custom_filter_init(self, operator=None, val=None, **kwargs):
    self.operator = operator
    self.__dict__['val'] = val
CustomFilter.__init__ = patched_custom_filter_init

df = pd.read_excel('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', sheet_name='Purchase Register', skiprows=8)
df = df[pd.to_datetime(df['Date'], errors='coerce').notna()]
df['Date'] = pd.to_datetime(df['Date'])
jan_df = df[df['Date'].dt.month == 1]
print("Voucher types in January:")
print(jan_df.groupby('Vch Type')['Gross Total'].sum())
