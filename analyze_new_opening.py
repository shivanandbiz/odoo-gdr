import pandas as pd
import numpy as np

def analyze_opening_balance():
    file_path = '/home/biz/odoo/new_gdr_Opening Balance apr 2025.xlsx'
    df = pd.read_excel(file_path, sheet_name='Trial Balance', header=None)
    
    # Identify data start
    # We saw data starts around row 11-12
    data = df.iloc[11:].copy()
    data.columns = ['Particulars', 'Col1', 'Col2', 'Debit', 'Credit']
    
    # Convert to numeric
    data['Debit'] = pd.to_numeric(data['Debit'], errors='coerce').fillna(0)
    data['Credit'] = pd.to_numeric(data['Credit'], errors='coerce').fillna(0)
    
    # Drop rows without particulars or without values (except if they are parent groups with NO value in current row)
    data = data.dropna(subset=['Particulars'])
    
    total_db = data['Debit'].sum()
    total_cr = data['Credit'].sum()
    
    # Find Grand Total row
    grand_total_row = data[data['Particulars'].str.contains('Grand Total', case=False, na=False)]
    if not grand_total_row.empty:
        gt_db = grand_total_row['Debit'].iloc[0]
        gt_cr = grand_total_row['Credit'].iloc[0]
        print(f"File Grand Total: Db={gt_db:,.2f}, Cr={gt_cr:,.2f}")
        print(f"Calculated Sum:   Db={total_db:,.2f}, Cr={total_cr:,.2f}")
        
        # Heuristic: If Sum(Rows) is approx 2x Grand Total, we have groups in the same column
        if abs(total_db - 2*gt_db) < 1.0:
            print("Detected duplicate totals (Groups + Ledgers in same column).")

    # To find ledgers in an alphabetical list with groups included:
    # Usually, groups and ledgers are both in the list.
    # If we filter out names that are likely groups (ALL CAPS or known group names),
    # and then check if the sum matches Grand Total.
    
    # Let's list the top 50 largest items and see which ones look like groups.
    largest_db = data.sort_values(by='Debit', ascending=False).head(20)
    largest_cr = data.sort_values(by='Credit', ascending=False).head(20)
    
    print("\nLargest Debits:")
    print(largest_db[['Particulars', 'Debit']])
    
    print("\nLargest Credits:")
    print(largest_cr[['Particulars', 'Credit']])

if __name__ == "__main__":
    analyze_opening_balance()
