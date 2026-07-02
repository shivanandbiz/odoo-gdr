import openpyxl

wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)
ws = wb['Balance Sheet']

for i, row in enumerate(ws.iter_rows(min_row=1, max_row=40, values_only=True)):
    print(f"Row {i+1}: {row}")
