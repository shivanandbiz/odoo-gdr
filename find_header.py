
import pandas as pd

file_path = "/home/biz/GDR_Original_Data/Final Data/Final_sales_Register_2025_2026.xlsx"
# Read first 50 rows to find header
df_head = pd.read_excel(file_path, header=None, nrows=50)
for i, row in df_head.iterrows():
    if 'Date' in row.values:
        print(f"Header found at row {i}")
        print(row.values)
        break
else:
    print("Header 'Date' not found in first 50 rows.")
    print("Sample rows:")
    print(df_head)
