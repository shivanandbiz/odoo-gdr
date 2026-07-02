import pandas as pd

def check_purchase_register():
    file_path = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
    try:
        df = pd.read_excel(file_path, sheet_name='Purchase Register')
        print("Columns:", df.columns.tolist())
        # Tally exports often have several header rows
        # Try to find actual data
        for i, row in df.iterrows():
            if 'Date' in row.values:
                 print(f"Found 'Date' at row index {i}")
                 # Re-read with correct header
                 df = pd.read_excel(file_path, sheet_name='Purchase Register', skiprows=i+1)
                 print("New Columns:", df.columns.tolist())
                 date_col = next((c for c in df.columns if 'date' in str(c).lower()), None)
                 amount_col = next((c for c in df.columns if 'gross' in str(c).lower() or 'total' in str(c).lower()), None)
                 if date_col and amount_col:
                      df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                      df = df.dropna(subset=[date_col])
                      df['month'] = df[date_col].dt.strftime('%Y-%m')
                      summary = df.groupby('month')[amount_col].sum()
                      print("\nSummary by Month:")
                      print(summary)
                 return
        
        # If not found headers, just show first 5 rows
        print("Header row not found. First 5 rows:")
        print(df.head())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_purchase_register()
