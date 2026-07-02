import pandas as pd

def preview_credit_notes():
    df = pd.read_excel('/home/biz/odoo/new_credit_note_register.xlsx', header=None)
    print("First 20 rows:")
    print(df.head(20).to_string())

preview_credit_notes()
