import pandas as pd

file_path = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
sheets = ['Contra Register', 'Debit Note Register', 'Journal Register', 'Credit Note Register', 'Receipt Register', 'Payment Register', 'Sales Inv. Register', 'Sales Inv. Register (2)', 'Purchase Register']

for sheet in sheets:
    print(f"\n--- Sheet: {sheet} ---")
    try:
        # Tally exports often have several header rows. I'll search for the row that looks like a header.
        df_full = pd.read_excel(file_path, sheet_name=sheet, nrows=20)
        print(df_full.head(10))
    except Exception as e:
        print(f"Error reading {sheet}: {e}")
