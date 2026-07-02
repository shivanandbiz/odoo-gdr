import pandas as pd
from datetime import datetime

def check_excel_totals(fname):
    print(f"Checking {fname}...")
    try:
        df = pd.read_excel(fname, sheet_name='Purchase Register')
    except Exception as e:
        print(f"Error reading {fname}: {e}")
        return

    # Find the header row
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

    # Filter out empty dates and rows that are totals
    df = df[df['Date'].notnull()]
    df = df[~df['Particulars'].astype(str).str.contains('Total|Grand', case=False, na=False)]
    
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df[df['Date'].notnull()]

    # Handle numeric columns
    gross_col = 'Gross Total'
    if gross_col not in df.columns:
        # Try to find a column that looks like gross total
        cols = [c for c in df.columns if 'Total' in str(c)]
        if cols:
            gross_col = cols[0]
            print(f"Using {gross_col} as Gross Total")
        else:
            print("Gross Total column not found.")
            return

    df[gross_col] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0)

    # Group by month and year
    df['MonthYear'] = df['Date'].dt.strftime('%Y-%m')
    monthly_totals = df.groupby('MonthYear')[gross_col].sum()
    
    print("\nMonthly Totals in Excel:")
    print(monthly_totals)
    print(f"\nGrand Total in Excel: {df[gross_col].sum():,.2f}")

check_excel_totals('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx')
