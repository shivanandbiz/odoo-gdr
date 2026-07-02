
import pandas as pd

file_path = "/home/biz/GDR_Original_Data/Final Data/Final_payment_register_2025_2026.xlsx"
# Read first few rows to find header
df = pd.read_excel(file_path, header=None, nrows=20)
print("Sample Rows:")
print(df)

# Look for header row
for i, row in df.iterrows():
    if 'Date' in row.values:
        print(f"\nHeader found at row {i}")
        print(row.values)
        break
