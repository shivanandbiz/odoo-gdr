import pandas as pd

def check_purchase_register():
    file_path = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
    try:
        # Tally exports often have company name at row 0, address 1-5, head at 6 or so.
        # Let's find 'Date' more robustly.
        df_full = pd.read_excel(file_path, sheet_name='Purchase Register', header=None)
        
        header_row = None
        for i, row in df_full.iterrows():
            if 'Date' in [str(v).strip() for v in row.values]:
                header_row = i
                break
        
        if header_row is not None:
            df = pd.read_excel(file_path, sheet_name='Purchase Register', skiprows=header_row+1)
            # Find Gross Total
            gross_col = next((c for c in df.columns if 'gross' in str(c).lower()), None)
            date_col = next((c for c in df.columns if 'date' in str(c).lower()), None)
            
            if date_col and gross_col:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                df = df.dropna(subset=[date_col])
                df['month'] = df[date_col].dt.strftime('%Y-%m')
                summary = df.groupby('month')[gross_col].sum()
                print("\nSummary by Month from all_tally_to_odoo_migratation.xlsx:")
                print(summary)
            else:
                print("Missing Date or Gross col")
        else:
            print("Date header not found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_purchase_register()
