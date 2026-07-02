import openpyxl

wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)
ws = wb['Journal Register']

for i, row in enumerate(ws.iter_rows(min_row=1380, max_row=1390, values_only=True)):
    print(f"Row {i+1380}: {row}")
