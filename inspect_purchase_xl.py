
import pandas as pd

file_path = "/home/biz/GDR_Original_Data/Final Data/Final_purchase_invoice.xlsx"
xls = pd.ExcelFile(file_path)
print("Sheet names:")
print(xls.sheet_names)

df = pd.read_excel(file_path, sheet_name='Sheet1', header=2)
print("First 50 rows:")
print(df.head(50))
