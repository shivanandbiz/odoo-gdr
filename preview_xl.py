import openpyxl

wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)
sheets_to_process = ['Contra Register', 'Debit Note Register', 'Journal Register', 'Credit Note Register', 'Receipt Register', 'Payment Register']

for sheet_name in sheets_to_process:
    print(f"\n--- {sheet_name} ---")
    ws = wb[sheet_name]
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i >= 10: break # Show first 10 rows
        print(row)
