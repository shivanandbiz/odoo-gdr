import pandas as pd

df = pd.read_excel('all_tally_to_odoo_migratation.xlsx', sheet_name='Purchase Register', skiprows=1, header=None)
print("Columns:", df.columns)

