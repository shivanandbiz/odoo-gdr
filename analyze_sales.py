import openpyxl
from datetime import datetime

def analyze_sales():
    wb = openpyxl.load_workbook('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', read_only=True, data_only=True)
    ws = wb['Sales Inv. Register']
    rows = list(ws.iter_rows(values_only=True))
    
    hdr_idx = None
    for i, row in enumerate(rows):
        if any(str(c).strip() == 'Date' for c in row if c is not None):
            hdr_idx = i
            break
            
    headers = [str(c).strip() if c is not None else f'Col{j}' for j, c in enumerate(rows[hdr_idx])]
    print('Headers:', headers)
    
    data = []
    for row in rows[hdr_idx+1:]:
        d = {h: v for h, v in zip(headers, row)}
        p = str(d.get('Particulars', '') or '').strip()
        if not p or 'Total' in p or 'Grand' in p or p == 'None':
            continue
        data.append(d)
        
    print('Records count:', len(data))
    
    gross_sum = 0
    monthly_gross = {}
    
    for d in data:
        try:
            val = float(str(d.get('Gross Total') or 0).strip() or 0)
            gross_sum += val
            
            # Month total
            dt = d.get('Date')
            if isinstance(dt, datetime):
                m = dt.strftime('%Y-%m')
                monthly_gross[m] = monthly_gross.get(m, 0) + val
        except:
            pass
            
    print('Total Gross:', f"{gross_sum:,.2f}")
    print('\nMonthly Breakdown:')
    for m in sorted(monthly_gross.keys()):
        print(f"{m}: {monthly_gross[m]:15,.2f}")

analyze_sales()
