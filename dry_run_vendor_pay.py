
import pandas as pd

def dry_run_vendor_payments(env):
    file_path = "/home/biz/GDR_Original_Data/Final Data/Final_payment_register_2025_2026.xlsx"
    df = pd.read_excel(file_path, header=8)
    
    print(f"Total Rows to process: {len(df)}")
    
    # Bank columns are from index 7 onwards
    bank_cols = df.columns.tolist()[7:]
    
    partners_missing = set()
    journals_missing = set()
    
    for idx, row in df.iterrows():
        part_name = str(row['Particulars']).strip()
        if not part_name or 'Total' in part_name or part_name == 'nan':
            continue
            
        # Find partner
        partner = env['res.partner'].search([('name', '=ilike', part_name)], limit=1)
        if not partner:
            partners_missing.add(part_name)
            
        # Find Bank column with value
        for b_col in bank_cols:
            val = row[b_col]
            if pd.notna(val) and float(val or 0) > 0:
                # Find Journal
                j_name = b_col
                journal = env['account.journal'].search([('name', 'ilike', j_name)], limit=1)
                if not journal:
                    # Fallback
                    if 'HDFC' in j_name: journal = env['account.journal'].search([('name', 'ilike', 'HDFC')], limit=1)
                    elif 'Kotak' in j_name: journal = env['account.journal'].search([('name', 'ilike', 'Kotak')], limit=1)
                    
                if not journal:
                    journals_missing.add(j_name)
                break

    print(f"\nMissing Partners: {len(partners_missing)}")
    print(list(partners_missing)[:10])
    print(f"\nMissing Journals: {len(journals_missing)}")
    print(list(journals_missing))

if __name__ == "__main__":
    dry_run_vendor_payments(env)
