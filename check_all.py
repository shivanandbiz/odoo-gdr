import openpyxl

wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)

for sheet_name in ['Contra Register', 'Debit Note Register', 'Journal Register', 'Credit Note Register', 'Receipt Register', 'Payment Register']:
    print(f"\n--- {sheet_name} ---")
    ws = wb[sheet_name]
    for i, row in enumerate(ws.iter_rows(min_row=11, max_row=20, values_only=True)):
        print(f"Row {i+11}: {row}")
