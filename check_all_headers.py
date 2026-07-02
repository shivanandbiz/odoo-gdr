import openpyxl

wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)
registers = ['Contra Register', 'Debit Note Register', 'Journal Register', 'Credit Note Register', 'Receipt Register', 'Payment Register']

for sheet_name in registers:
    print(f"\n--- {sheet_name} ---")
    ws = wb[sheet_name]
    # Rows 0-7 are usually company info
    for i, row in enumerate(ws.iter_rows(min_row=9, max_row=12, values_only=True)):
        print(f"Row {i+9}: {row}")
