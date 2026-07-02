import openpyxl

wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)
sheets_to_process = ['Contra Register', 'Debit Note Register', 'Journal Register', 'Credit Note Register', 'Receipt Register', 'Payment Register']

for sheet_name in sheets_to_process:
    print(f"\n--- {sheet_name} ---")
    ws = wb[sheet_name]
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i < 8: continue # Skip company headers
        if i >= 20: break # Show rows 8 to 20
        print(row)
