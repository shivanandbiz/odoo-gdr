import pandas as pd

file_path = '/home/biz/odoo/customer_gdr.xlsx'
df = pd.read_excel(file_path)
print(df.head(10).to_string())
print("\nUnique GST Treatments:", df['l10n_in_gst_treatment'].unique())
