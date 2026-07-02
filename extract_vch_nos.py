
import pandas as pd
import numpy as np

file_path = "/home/biz/GDR_Original_Data/Final Data/Final_sales_Register_2025_2026.xlsx"
df = pd.read_excel(file_path, header=8) # Row 8 is the header

# Drop empty rows and rows that are totals or headers
df = df[df['Date'].notna()]
df = df[df['Vch No.'].notna()]
df = df[df['Vch No.'] != 'Vch No.'] # Avoid header repeat

# Sometimes Tally exports have strings like ' (Total)' in particulars
df = df[~df['Particulars'].astype(str).str.contains('Total', na=False, case=False)]

vch_nos = df['Vch No.'].unique().tolist()
print(f"Total Unique Voucher Numbers in Excel: {len(vch_nos)}")
print("Sample Voucher Numbers:", vch_nos[:10])

# Save the list of voucher numbers for comparison
with open('excel_vch_nos.txt', 'w') as f:
    for vch in vch_nos:
        f.write(f"{vch}\n")
