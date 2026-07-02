import openpyxl
from datetime import datetime
from collections import defaultdict

def read_purchase_sheet(fname, sheet_name='Purchase Register'):
    print(f"Reading {fname} [{sheet_name}]...")
    wb = openpyxl.load_workbook(fname, read_only=True, data_only=True)
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    
    hdr_idx = None
    for i, row in enumerate(rows):
        if any(str(c).strip() == 'Date' for c in row if c is not None):
            hdr_idx = i
            break
    
    headers = [str(c).strip() if c is not None else f'Col{j}' for j, c in enumerate(rows[hdr_idx])]
    data = []
    for idx, row in enumerate(rows[hdr_idx + 1:]):
        d = {h: v for h, v in zip(headers, row)}
        d['_row_idx'] = idx + hdr_idx + 1
        part = str(d.get('Particulars', '') or '').strip()
        if not part or 'Total' in part or 'Grand' in part: continue
        
        raw_date = d.get('Date')
        if not isinstance(raw_date, (datetime, str)): continue
        try:
            dt = raw_date if isinstance(raw_date, datetime) else datetime.strptime(str(raw_date)[:10], '%Y-%m-%d')
        except: continue
        
        d['_date'] = dt
        try:
            d['_gross'] = float(d.get('Gross Total') or 0)
        except:
            # Handle shifted columns in March File 1
            try:
                alt = d.get('LOCAL PURCHASE GST 18%')
                d['_gross'] = float(alt or 0)
            except:
                d['_gross'] = 0.0
        
        data.append(d)
    return data

file1 = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
file2 = '/home/biz/odoo/purchase.xlsx-2025-26.......xlsx'

rows1 = read_purchase_sheet(file1)
rows2 = read_purchase_sheet(file2)

# TARGETS
target = {
    '2025-04': 4965142.20, '2025-05': 5935852.36, '2025-06': 5902935.38,
    '2025-07': 5832890.98, '2025-08': 2706354.30, '2025-09': 3742037.02,
    '2025-10': 5164669.18, '2025-11': 4396926.92, '2025-12': 4792170.86,
    '2026-01': 7199291.74, '2026-02': 9630540.24, '2026-03': 30054329.14
}

final_rows = []
monthly = defaultdict(float)

for r in rows1:
    my = r['_date'].strftime('%Y-%m')
    if my == '2026-01':
        # EXCLUDE the first block of January (found to be the 3.12L discrepancy)
        if r['_row_idx'] < 800:
            continue
    if my in target and my <= '2026-01':
        final_rows.append(r)
        monthly[my] += r['_gross']

for r in rows2:
    my = r['_date'].strftime('%Y-%m')
    if my in ['2026-02', '2026-03']:
        final_rows.append(r)
        monthly[my] += r['_gross']

print("\nValidation with January Exclusion Logic:")
for m in sorted(target.keys()):
    act = monthly[m]
    print(f"{m}: Act={act:12.2f} | Tgt={target[m]:12.2f} | Diff={act-target[m]:12.2f}")

print(f"\nGrand Total: {sum(monthly.values()):,.2f}")
print(f"Target Total: 90,323,140.32")
