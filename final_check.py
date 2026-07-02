import openpyxl

wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)

for sheet_name in ['Receipt Register', 'Payment Register']:
    print(f"\n--- {sheet_name} ---")
    ws = wb[sheet_name]
    # Check Row 9 (Head), then 11, 12, 13
    for i, row in enumerate(ws.iter_rows(min_row=9, max_row=15, values_only=True)):
        print(f"Row {i+9}: {row}")
