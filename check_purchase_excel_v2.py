import pandas as pd

def check_excel():
    file_path = '/home/biz/odoo/purchase.xlsx-2025-26.......xlsx'
    try:
        # Try to find the actual table by skipping rows until we find 'Date'
        for skip in range(1, 20):
            df = pd.read_excel(file_path, skiprows=skip)
            cols = [str(c).strip().lower() for c in df.columns]
            if 'date' in cols:
                print(f"Found table at row {skip}")
                print("Columns found:", df.columns.tolist())
                
                date_col = next((c for c in df.columns if 'date' in str(c).lower()), None)
                amount_col = next((c for c in df.columns if 'amount' in str(c).lower() or 'total' in str(c).lower() or 'gross' in str(c).lower()), None)
                
                if date_col and amount_col:
                     df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                     df = df.dropna(subset=[date_col])
                     df['month'] = df[date_col].dt.strftime('%Y-%m')
                     summary = df.groupby('month')[amount_col].sum()
                     print("\nSummary by Month from Excel:")
                     print(summary)
                     return
        
        print("Could not find 'Date' column in the first 20 rows.")
    except Exception as e:
        print(f"Error reading Excel: {e}")

if __name__ == "__main__":
    check_excel()
