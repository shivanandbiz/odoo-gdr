import pandas as pd

def preview_debit_notes():
    df = pd.read_excel('/home/biz/odoo/new_debit_note_register.xlsx', header=None)
    print("First 20 rows:")
    print(df.head(20).to_string())
    print("\nColumns and shapes:")
    print(df.shape)

preview_debit_notes()
