
import pandas as pd
import numpy as np

def get_excel_fingerprints():
    file_path = "/home/biz/GDR_Original_Data/Final Data/Final_sales_Register_2025_2026.xlsx"
    df = pd.read_excel(file_path, header=8)
    df = df[df['Date'].notna() & df['Vch No.'].notna()]
    df = df[~df['Particulars'].astype(str).str.contains('Total', na=False, case=False)]
    
    fingerprints = []
    for _, row in df.iterrows():
        # Date, Particulars (Partner), Debit (Amount), Vch No.
        date = str(row['Date']).split(' ')[0]
        partner = str(row['Particulars']).strip()
        amount = float(row['Debit']) if not pd.isna(row['Debit']) else 0.0
        vch_no = str(row['Vch No.']).strip()
        fingerprints.append({
            'date': date,
            'partner': partner,
            'amount': round(amount, 2),
            'vch_no': vch_no
        })
    return fingerprints

def get_odoo_fingerprints(env):
    invoices = env['account.move'].search([('move_type', '=', 'out_invoice')])
    fingerprints = []
    for inv in invoices:
        fingerprints.append({
            'date': str(inv.invoice_date),
            'partner': inv.partner_id.name.strip() if inv.partner_id else '',
            'amount': round(inv.amount_total, 2),
            'name': inv.name,
            'ref': inv.ref
        })
    return fingerprints

def compare():
    excel_fps = get_excel_fingerprints()
    odoo_fps = get_odoo_fingerprints(env)
    
    print(f"Excel count: {len(excel_fps)}")
    print(f"Odoo count: {len(odoo_fps)}")
    
    missing = []
    for ex in excel_fps:
        match = False
        for od in odoo_fps:
            # Check for match. Partner name might be slightly different.
            # Amount and Date should be exact.
            if ex['date'] == od['date'] and abs(ex['amount'] - od['amount']) < 0.01:
                # Optional: check partner name subset
                if ex['partner'].lower() in od['partner'].lower() or od['partner'].lower() in ex['partner'].lower():
                    match = True
                    break
        if not match:
            missing.append(ex)
            
    print(f"Missing from Odoo ({len(missing)}):")
    for m in missing:
        print(m)

if __name__ == "__main__":
    compare()
