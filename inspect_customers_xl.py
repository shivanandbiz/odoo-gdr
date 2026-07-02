import pandas as pd

file_path = '/home/biz/odoo/customer_gdr.xlsx'
try:
    df = pd.read_excel(file_path)
    print("ALL COLUMNS:")
    for i, col in enumerate(df.columns):
        print(f"{i}: {col}")
    
    # Check for empty/NaN columns
    print("\nColumn Null Counts:")
    print(df.isnull().sum())

except Exception as e:
    print(f"Error reading file: {e}")
