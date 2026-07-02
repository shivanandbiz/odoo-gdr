# verify_totals.py
import openpyxl

wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)
sheets = ['Contra Register', 'Journal Register', 'Receipt Register', 'Payment Register', 'Debit Note Register', 'Credit Note Register']

excel_totals = {}
for s in sheets:
    ws = wb[s]
    tot = 0
    for i, row in enumerate(ws.iter_rows(min_row=11, values_only=True)):
        if not any(row): continue
        if row[1] and ('Total' in str(row[1]) or 'Grand' in str(row[1])): break
        
        # Identify Dr/Cr. For non-columnar (Receipt/Pay) it's row[4]/row[5]
        try:
            if s in ['Receipt Register', 'Payment Register']:
                tot += float(row[4] or 0) + float(row[5] or 0)
            else:
                # Columnar. Gross Total is row[3]
                tot += float(row[3] or 0)
        except: pass
    excel_totals[s] = tot

print("--- EXCEL TOTALS (Sum of Amount) ---")
for s,v in excel_totals.items(): print(f"{s}: {v}")

print("\n--- ODOO TOTALS ---")
for s in sheets:
    ref_pattern = s.replace(' Register', '')
    # Odoo query:
    env.cr.execute("SELECT sum(debit) FROM account_move_line WHERE ref LIKE %s", (ref_pattern + '%',))
    odoo_tot = env.cr.fetchone()[0] or 0.0
    print(f"{s} (ref like {ref_pattern}%): {odoo_tot}")
