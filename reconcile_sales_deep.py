
import pandas as pd

def reconcile_sales():
    print("=== RECONCILING SALES INVOICES (Excel vs Odoo) ===")
    
    # Load Excel
    df1 = pd.read_excel('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', sheet_name='Sales Inv. Register', skiprows=8)
    df2 = pd.read_excel('/home/biz/odoo/Sales Inv. Register (2).xlsx', skiprows=8) # Wait, checking filename
    # I'll check filenames first
    
if __name__ == '__main__':
    reconcile_sales()
