import pandas as pd
import psycopg2

def compare_with_purchase_file():
    file_path = '/home/biz/odoo/purchase.xlsx-2025-26.......xlsx'
    try:
        df_xl = pd.read_excel(file_path, skiprows=8)
        df_xl['Date'] = pd.to_datetime(df_xl['Date'], errors='coerce')
        df_xl = df_xl[df_xl['Date'].dt.month == 2]
        # Clean up
        xl_bills = []
        for _, row in df_xl.iterrows():
            ref = str(row['Supplier Invoice No.']).strip()
            total = float(row['Gross Total'])
            if ref and ref != 'nan':
                 xl_bills.append({'ref': ref, 'total': round(total, 2)})
        print(f"Total in {file_path} for Feb: {len(xl_bills)}")
        print(f"Sum of Gross Total: {sum(b['total'] for b in xl_bills):,.2f}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    compare_with_purchase_file()
