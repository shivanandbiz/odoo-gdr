import pandas as pd

def check_excel():
    file_path = '/home/biz/odoo/purchase.xlsx-2025-26.......xlsx'
    try:
        df = pd.read_excel(file_path)
        print("Columns found:", df.columns.tolist())
        
        # Try to find Date and Amount columns
        date_col = next((c for c in df.columns if 'date' in c.lower()), None)
        amount_col = next((c for c in df.columns if 'amount' in c.lower() or 'total' in c.lower() or 'gross' in c.lower()), None)
        
        if date_col and amount_col:
             df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
             df['month'] = df[date_col].dt.strftime('%Y-%m')
             summary = df.groupby('month')[amount_col].sum()
             print("\nSummary by Month from Excel:")
             print(summary)
        else:
             print("Could not identify Date or Amount columns automatically.")
             print("First 5 rows:")
             print(df.head())
    except Exception as e:
        print(f"Error reading Excel: {e}")

if __name__ == "__main__":
    check_excel()
