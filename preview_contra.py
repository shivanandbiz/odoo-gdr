import openpyxl

wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)
sheet_name = 'Contra Register'
ws = wb[sheet_name]
for i, row in enumerate(ws.iter_rows(values_only=True)):
    if i < 8: continue
    if i >= 50: break # Show more rows to find the multi-line entry
    print(row)
