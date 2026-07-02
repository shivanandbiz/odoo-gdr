
import pandas as pd

file_path = "/home/biz/GDR_Original_Data/Final Data/Final_sales_Register_2025_2026.xlsx"
df = pd.read_excel(file_path, header=8)
missing_vchs = ['GDRM/25-26/02', 'GDRM/25-26/04', 'GDRM/25-26/26', 'GDRM/25-26/59', 'GDRM/25-26/117', 'GDRM/25-26/157', 'GDRM/25-26/158']

for vch in missing_vchs:
    rows = df[df['Vch No.'] == vch]
    for _, row in rows.iterrows():
        print(f"Vch: {vch} | Date: {row['Date']} | Part: {row['Particulars']} | Debit: {row['Debit']}")
