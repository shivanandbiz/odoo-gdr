
import pandas as pd

df = pd.read_excel('/home/biz/GDR_Original_Data/Final Data/Final_recipt_register_2025_2026.xlsx', skiprows=8)
row = df[df['Gross Total'] == 15330796.0].iloc[0]
print(f"Date: {row['Date']}, Part: {row['Particulars']}, Ref: {row['Voucher Ref. No.']}, Amount: {row['Gross Total']}")
