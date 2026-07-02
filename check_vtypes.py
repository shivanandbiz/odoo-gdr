import openpyxl

wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)
ws = wb['Payment Register']

vch_types = {}
for i, row in enumerate(ws.iter_rows(min_row=11, values_only=True)):
    v_type = str(row[2])
    vch_types[v_type] = vch_types.get(v_type, 0) + 1

print(f"Vch Types in Payment Register: {vch_types}")
