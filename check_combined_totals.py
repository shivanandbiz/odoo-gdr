# check_combined_totals.py
import pandas as pd

def get_df(filename, skip):
    df = pd.read_excel(filename, sheet_name='Purchase Register', skiprows=skip)
    df.columns = df.columns.str.strip()
    df = df[pd.to_datetime(df['Date'], errors='coerce').notna()]
    df['Date'] = pd.to_datetime(df['Date'])
    df['Gross Total'] = pd.to_numeric(df['Gross Total'], errors='coerce').fillna(0)
    return df

f1 = get_df('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', 8)
f2 = get_df('/home/biz/odoo/purchase.xlsx-2025-26.......xlsx', 8)

# Combine and drop duplicates
combined = pd.concat([f1, f2], ignore_index=True)
# Duplicates based on Date, Supplier Invoice No, and Gross Total
combined_unique = combined.drop_duplicates(subset=['Date', 'Supplier Invoice No.', 'Gross Total'], keep='last')

combined_unique['MonthIndex'] = combined_unique['Date'].dt.month
combined_unique['MonthName'] = combined_unique['Date'].dt.month_name()
# Sort for presentation
combined_unique['MonthSort'] = combined_unique['Date'].dt.strftime('%m-%B')

monthly = combined_unique.groupby('MonthSort')['Gross Total'].sum()
print("\n--- COMBINED UNIQUE TOTALS ---")
print(monthly)
print("GRAND TOTAL:", combined_unique['Gross Total'].sum())
