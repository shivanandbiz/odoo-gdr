import pandas as pd
import psycopg2
import json

def compare_february():
    # 1. Read Excel
    try:
        df_xl = pd.read_excel('/home/biz/odoo/feb.xlsx', skiprows=8)
        df_xl['Date'] = pd.to_datetime(df_xl['Date'], errors='coerce')
        df_xl = df_xl.dropna(subset=['Date'])
        xl_bills = []
        for _, row in df_xl.iterrows():
            ref = str(row['Supplier Invoice No.']).strip()
            total = float(row['Gross Total'])
            vendor = str(row['Particulars']).strip()
            if ref and ref != 'nan':
                xl_bills.append({'ref': ref, 'total': round(total, 2), 'vendor': vendor})
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    # 2. Read Odoo
    conn = psycopg2.connect(dbname='Odoo', user='odoo', password='odoo', host='localhost')
    cur = conn.cursor()
    cur.execute("""
        SELECT ref, amount_total, (SELECT name FROM res_partner WHERE id = partner_id) as vendor 
        FROM account_move 
        WHERE move_type = 'in_invoice' AND state = 'posted' AND TO_CHAR(date, 'YYYY-MM') = '2026-02'
    """)
    odoo_bills = []
    for ref, total, vendor in cur.fetchall():
        odoo_bills.append({'ref': str(ref).strip(), 'total': round(float(total), 2), 'vendor': vendor})
    
    # 3. Compare
    xl_refs = [b['ref'] for b in xl_bills]
    odoo_refs = [b['ref'] for b in odoo_bills]
    
    missing_in_odoo = [b for b in xl_bills if b['ref'] not in odoo_refs]
    extra_in_odoo = [b for b in odoo_bills if b['ref'] not in xl_refs]
    mismatched = []
    
    for xb in xl_bills:
        for ob in odoo_bills:
            if xb['ref'] == ob['ref'] and abs(xb['total'] - ob['total']) > 10.0:
                mismatched.append({'ref': xb['ref'], 'xl_total': xb['total'], 'odoo_total': ob['total'], 'vendor': xb['vendor']})

    print(f"Summary for February 2026:")
    print(f"Bills in Excel: {len(xl_bills)}")
    print(f"Bills in Odoo: {len(odoo_bills)}")
    print(f"\n--- MISSING IN ODOO ({len(missing_in_odoo)}) ---")
    for b in missing_in_odoo:
        print(f"Ref: {b['ref']} | Total: {b['total']} | Vendor: {b['vendor']}")
        
    print(f"\n--- EXTRA IN ODOO ({len(extra_in_odoo)}) ---")
    for b in extra_in_odoo:
        print(f"Ref: {b['ref']} | Total: {b['total']} | Vendor: {b['vendor']}")
        
    print(f"\n--- AMOUNT MISMATCH ({len(mismatched)}) ---")
    for b in mismatched:
        print(f"Ref: {b['ref']} | Excel: {b['xl_total']} | Odoo: {b['odoo_total']} | Vendor: {b['vendor']}")

if __name__ == "__main__":
    compare_february()
