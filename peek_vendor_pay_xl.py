
import pandas as pd

file_path = "/home/biz/GDR_Original_Data/Final Data/Final_payment_register_2025_2026.xlsx"
df = pd.read_excel(file_path, header=8)
print("Columns:", df.columns.tolist())
print("Total rows:", len(df))
print("\nFirst 3 data rows:")
print(df.head(3))
