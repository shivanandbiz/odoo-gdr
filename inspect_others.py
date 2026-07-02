import openpyxl

def inspect_sheet(name):
    print(f"\n--- {name} ---")
    wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)
    ws = wb[name]
    rows = list(ws.iter_rows(values_only=True, max_row=15))
    
    for i, row in enumerate(rows):
        print(f"Row {i}: {list(row)}")

inspect_sheet('Receipt Register')
inspect_sheet('Payment Register')
inspect_sheet('Journal Register')
