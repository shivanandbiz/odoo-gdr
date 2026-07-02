# verify_totals_v2.py
import openpyxl

wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)

# Register Mapping for Ref search
mapping = {
    'Contra Register': 'Contra',
    'Journal Register': 'Journal',
    'Receipt Register': 'Receipt',
    'Payment Register': 'Bank Payment',
    'Debit Note Register': 'Debit Note',
    'Credit Note Register': 'Credit Note'
}

excel_totals = {}
for s, ref_term in mapping.items():
    ws = wb[s]
    tot = 0
    for i, row in enumerate(ws.iter_rows(min_row=11, values_only=True)):
        if not any(row): continue
        if row[1] and ('Total' in str(row[1]) or 'Grand' in str(row[1])): break
        try:
            if s in ['Receipt Register', 'Payment Register']:
                tot += float(row[4] or 0) + float(row[5] or 0)
            else:
                tot += float(row[3] or 0)
        except: pass
    excel_totals[s] = tot

print("--- RECONCILIATION ---")
for s, ref_term in mapping.items():
    excel_val = excel_totals[s]
    # Odoo
    count = env['account.move'].search_count([('ref', 'like', ref_term + ' %')])
    env.cr.execute("SELECT sum(debit) FROM account_move_line WHERE ref LIKE %s", (ref_term + ' %',))
    odoo_val = env.cr.fetchone()[0] or 0.0
    print(f"{s}: Excel={excel_val:,.2f}, Odoo={odoo_val:,.2f} (Count: {count})")
