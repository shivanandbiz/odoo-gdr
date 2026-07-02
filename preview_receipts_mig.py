import pandas as pd

def preview_receipts():
    df = pd.read_excel('/home/biz/odoo/new_recipt_register_mig.xlsx', header=None)
    print("First 20 rows:")
    print(df.head(20).to_string())

preview_receipts()
