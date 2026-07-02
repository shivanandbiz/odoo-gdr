import pandas as pd
from datetime import datetime

def check_excel_totals(fname):
    print(f"Checking {fname}...")
    try:
        df = pd.read_excel(fname, sheet_name='Purchase Register')
    except Exception as e:
        print(f"Error reading {fname}: {e}")
        return

    hdr_idx = None
    for i, row in df.iterrows():
        if any(str(c).strip() == 'Date' for c in row if pd.notnull(c)):
            hdr_idx = i
            break
    
    if hdr_idx is None:
        print("Header 'Date' not found.")
        return

    df.columns = [str(c).strip() for c in df.iloc[hdr_idx]]
    df = df.iloc[hdr_idx+1:].reset_index(drop=True)
    df = df[df['Date'].notnull()]
    df = df[~df['Particulars'].astype(str).str.contains('Total|Grand', case=False, na=False)]
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df[df['Date'].notnull()]

    gross_col = 'Gross Total'
    if gross_col not in df.columns:
        cols = [c for c in df.columns if 'Total' in str(c)]
        if cols: gross_col = cols[0]
        else: return

    df[gross_col] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0)
    df['MonthYear'] = df['Date'].dt.strftime('%Y-%m')
    monthly_totals = df.groupby('MonthYear')[gross_col].sum()
    
    print("\nMonthly Totals in Excel:")
    print(monthly_totals)
    print(f"\nGrand Total in Excel: {df[gross_col].sum():,.2f}")

print("--- File 1 ---")
check_excel_totals('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx')
print("\n--- File 2 ---")
check_excel_totals('/home/biz/odoo/purchase.xlsx-2025-26.......xlsx')
