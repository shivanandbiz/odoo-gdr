
import pandas as pd
from datetime import datetime

FILE_PATH = '/home/biz/GDR_Original_Data/Final Data/Final_sales_Register_2025_2026.xlsx'
df = pd.read_excel(FILE_PATH, header=None)

for i in range(25, 40):
    row = df.iloc[i]
    date = row.iloc[0]
    inv_no = str(row.iloc[2]) if not pd.isna(row.iloc[2]) else ""
    party = str(row.iloc[3]) if not pd.isna(row.iloc[3]) else ""
    
    is_date = isinstance(date, (datetime, pd.Timestamp))
    is_gdr = inv_no.startswith('GDR/')
    
    print(f"Row {i}: Date={date} ({type(date)}) Inv={inv_no} Party={party} | is_date={is_date} is_gdr={is_gdr}")
