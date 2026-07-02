import pandas as pd

file_path = '/home/biz/odoo/customer_gdr.xlsx'
df = pd.read_excel(file_path)
nan_name_df = df[df['complete_name'].isna()]
print(f"Sample rows with missing complete_name (Total: {len(nan_name_df)}):")
print(nan_name_df.head(20).to_string())
