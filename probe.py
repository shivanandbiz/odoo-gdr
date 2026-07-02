import pandas as pd
df = pd.read_excel('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', sheet_name='Purchase Register', skiprows=8)
print(df.columns)
print(df.head(2))
