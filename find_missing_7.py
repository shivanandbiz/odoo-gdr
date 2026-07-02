
def find_missing_7(env):
    import pandas as pd
    file_path = "/home/biz/GDR_Original_Data/Final Data/Final_sales_Register_2025_2026.xlsx"
    df = pd.read_excel(file_path, header=8)
    excel_vch_nos = df[df['Date'].notna() & df['Vch No.'].notna()]['Vch No.'].unique().tolist()
    excel_set = set(str(v).strip() for v in excel_vch_nos)
    
    invoices = env['account.move'].search([('move_type', '=', 'out_invoice')])
    odoo_set = set()
    for inv in invoices:
        if inv.ref:
            odoo_set.add(str(inv.ref).strip())
        if inv.name:
            odoo_set.add(str(inv.name).strip())
            
    missing = [v for v in sorted(list(excel_set)) if v not in odoo_set]
    print(f"Total Unique in Excel: {len(excel_set)}")
    print(f"Total in Odoo: {len(invoices)}")
    print(f"Missing from Excel ({len(missing)}):")
    for m in missing:
        print(m)

if __name__ == "__main__":
    find_missing_7(env)
