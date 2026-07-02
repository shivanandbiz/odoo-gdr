
import pandas as pd

file_path = "/home/biz/GDR_Original_Data/Final Data/Final_sales_Register_2025_2026.xlsx"
df = pd.read_excel(file_path)
print("Columns:", df.columns.tolist())
print("First 5 rows:")
print(df.head())
print("Total rows:", len(df))
