# check_purchase_totals_v2.py
import pandas as pd

def check_file(filename, skip):
    print(f"\n--- {filename} ---")
    try:
        df = pd.read_excel(filename, sheet_name='Purchase Register', skiprows=skip)
        
        # Strip whitespace from columns
        df.columns = df.columns.str.strip()
        
        # Identify the gross total column
        gross_col = 'Gross Total'
        if gross_col not in df.columns:
            print(f"Columns: {df.columns.tolist()}")
            return None
        
        # Filter rows with valid dates
        df['DateProcessed'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df[pd.to_datetime(df['Date'], errors='coerce').notna()]
        
        # Clean amount
        df[gross_col] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0)
        
        # Get Month for grouping
        df['MonthGroup'] = df['DateProcessed'].dt.strftime('%m-%B')
        
        monthly = df.groupby('MonthGroup')[gross_col].sum()
        print(monthly)
        print("GRAND TOTAL:", df[gross_col].sum())
        return df
    except Exception as e:
        print(f"ERROR: {e}")
        return None

check_file('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', 8)
check_file('/home/biz/odoo/purchase.xlsx-2025-26.......xlsx', 8)
