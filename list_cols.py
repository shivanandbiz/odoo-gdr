
import pandas as pd

df = pd.read_excel("/home/biz/GDR_Original_Data/Final Data/Final_payment_register_2025_2026.xlsx", header=8)
cols = df.columns.tolist()
for i, c in enumerate(cols):
    print(f"{i}: {c}")
