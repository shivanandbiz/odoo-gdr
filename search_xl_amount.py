
import pandas as pd

def find_in_excel():
    file_path = '/home/biz/GDR_Original_Data/Final Data/Final_recipt_register_2025_2026.xlsx'
    df = pd.read_excel(file_path, skiprows=8)
    # Search for specific amount: 15330796.0
    matches = df[df['Gross Total'] == 15330796.0]
    print(matches[['Date', 'Particulars', 'Voucher Ref. No.', 'Gross Total']])

if __name__ == "__main__":
    find_in_excel()
