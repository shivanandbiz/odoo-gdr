import openpyxl

wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)
ws = wb['Receipt Register']
for i, row in enumerate(ws.iter_rows(min_row=11, max_row=25, values_only=True)):
    print(f"Row {i+11}: {row}")
