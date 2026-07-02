import pandas as pd

def check_excel():
    file_path = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
    try:
        xls = pd.ExcelFile(file_path)
        print("Sheets found:", xls.sheet_names)
        for sheet in xls.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet)
            print(f"\nAnalyzing sheet: {sheet}")
            date_col = next((c for c in df.columns if 'date' in str(c).lower()), None)
            amount_col = next((c for c in df.columns if 'amount' in str(c).lower() or 'total' in str(c).lower() or 'gross' in str(c).lower() or 'debit' in str(c).lower()), None)
            
            if date_col and amount_col:
                 df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                 df = df.dropna(subset=[date_col])
                 df['month'] = df[date_col].dt.strftime('%Y-%m')
                 summary = df.groupby('month')[amount_col].sum()
                 print(summary)
            else:
                 print("Could not find Date/Amount columns in this sheet.")
    except Exception as e:
        print(f"Error reading Excel: {e}")

if __name__ == "__main__":
    check_excel()
