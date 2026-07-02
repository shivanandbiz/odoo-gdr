
import pandas as pd
import odoo
from odoo import api, SUPERUSER_ID

def reconcile():
    print("=== DEEP SALES RECONCILIATION ===")
    
    # 1. Load Excel Data
    excel_path = '/home/biz/odoo/all_tally_to_odoo_migratation.xlsx'
    
    # Sheet 1
    df1 = pd.read_excel(excel_path, sheet_name='Sales Inv. Register', skiprows=8)
    df1 = df1[df1['Voucher Ref. No.'].notna()]
    
    # Sheet 2
    df2 = pd.read_excel(excel_path, sheet_name='Sales Inv. Register (2)', skiprows=8)
    # Correct column names if needed
    if 'Voucher Ref. No.' not in df2.columns:
        # Map based on position or likely names
        df2.columns = [c.strip() if isinstance(c, str) else c for c in df2.columns]
        # Assuming Voucher Type is at some column... let's just use what we found earlier
    
    # Combine Excel Unique Vouchers
    # For now, let's just use what was imported in Odoo and compare with the Grand Total Target (120M)
    
    print(f"Excel Sheet 1 Rows: {len(df1)}")
    
    # 2. Extract Odoo Invoices
    conf_file = '/home/biz/odoo/odoo.conf'
    odoo.tools.config.parse_config(['-c', conf_file])
    registry = odoo.modules.registry.Registry(odoo.tools.config['db_name'])
    
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        invoices = env['account.move'].search([('move_type', '=', 'out_invoice'), ('state', '=', 'posted')])
        
        odoo_data = []
        for inv in invoices:
            odoo_data.append({
                'ref': inv.ref,
                'name': inv.name,
                'amount': inv.amount_total,
                'date': inv.date
            })
        
        df_odoo = pd.DataFrame(odoo_data)
        print(f"Odoo Invoices: {len(df_odoo)} | Total: {df_odoo['amount'].sum():,.2f}")
        
        # 3. Target Check
        target = 120373470.75 # From Tally Image
        print(f"Tally Target: {target:,.2f}")
        print(f"Difference:   {df_odoo['amount'].sum() - target:,.2f}")
        
        # 4. Monthly Breakdown
        df_odoo['month'] = pd.to_datetime(df_odoo['date']).dt.strftime('%Y-%m')
        monthly = df_odoo.groupby('month')['amount'].sum()
        print("\nMonthly Totals in Odoo:")
        print(monthly)

if __name__ == '__main__':
    reconcile()
