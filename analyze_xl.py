import pandas as pd

xl_path = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
xl = pd.ExcelFile(xl_path)

registers = ['Contra Register', 'Debit Note Register', 'Journal Register', 'Credit Note Register', 'Receipt Register', 'Payment Register']

for sheet in registers:
    print(f"\n--- {sheet} ---")
    df = pd.read_excel(xl, sheet_name=sheet)
    print("Columns:", df.columns.tolist())
    print("Head:\n", df.head(3))
    print("-" * 30)
