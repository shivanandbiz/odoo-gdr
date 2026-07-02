
import pandas as pd
from datetime import datetime

def migrate_final_sales():
    file_path = "/home/biz/odoo/all_tally_to_odoo_migratation.xlsx"
    print(f"Reading {file_path} ...")
    
    # Read the file
    df = pd.read_excel(file_path, sheet_name='Sales Inv. Register', header=8)
    
    # Remove rows without Date or Particulars
    df = df[df['Date'].notna() & df['Particulars'].notna()].copy()
    # Filter out footer typical of Tally exports
    df = df[~df['Particulars'].str.contains('Grand Total', na=False)]
    
    print(f"Found {len(df)} rows to process.")

    # 1. DELETE existing sales invoices
    print("Deleting existing sales invoices...")
    existing = env['account.move'].search([('move_type', '=', 'out_invoice')])
    if existing:
        existing.button_draft()
        existing.unlink()
        env.cr.commit()
    print("  Cleaned existing.")

    # Caches
    partner_cache = {}
    product_cache = {}
    tax_cache = {}
    
    account_income = env['account.account'].search([('account_type', '=', 'income')], limit=1)
    journal = env['account.journal'].search([('type', '=', 'sale')], limit=1)

    def get_partner(name):
        name = str(name).strip()
        if name not in partner_cache:
            p = env['res.partner'].search([('name', '=', name)], limit=1)
            if not p:
                p = env['res.partner'].create({'name': name, 'customer_rank': 1, 'is_company': True})
                env.cr.commit()
            partner_cache[name] = p
        return partner_cache[name]

    def get_product(name):
        name = str(name).strip()
        if name not in product_cache:
            p = env['product.product'].search([('name', '=', name)], limit=1)
            if not p:
                p = env['product.product'].create({
                    'name': name,
                    'type': 'service',
                    'sale_ok': True,
                })
            product_cache[name] = p
        return product_cache[name]

    def get_taxes(row):
        # Determine if Interstate or Local
        igst = row.get('IGST@18', 0)
        cgst = row.get('CGST @ 9%', 0)
        
        try:
            igst = float(igst) if pd.notna(igst) else 0.0
            cgst = float(cgst) if pd.notna(cgst) else 0.0
        except:
            igst, cgst = 0.0, 0.0
        
        if igst > 0:
            tax = env['account.tax'].search([('amount', '=', 18), ('type_tax_use', '=', 'sale'), ('name', 'ilike', 'IGST')], limit=1)
            if not tax:
                tax = env['account.tax'].search([('amount', '=', 18), ('type_tax_use', '=', 'sale')], limit=1)
            return tax
        else:
            # Default to 18% sale tax
            tax = env['account.tax'].search([('amount', '=', 18), ('type_tax_use', '=', 'sale')], limit=1)
            if not tax:
                tax = env['account.tax'].create({'name': 'GST 18%', 'amount': 18, 'type_tax_use': 'sale'})
            return tax

    created_count = 0
    for idx, row in df.iterrows():
        try:
            date = row.get('Date')
            if pd.isna(date): continue
            
            part_name = str(row.get('Particulars', '')).strip()
            if not part_name or part_name.lower() == 'nan': continue
            
            partner = get_partner(part_name)
            ref = str(row.get('Voucher Ref. No.', '')).strip()
            if not ref or ref.lower() == 'nan': ref = f"SALES_MIG_{idx}"
            
            gross = row.get('Gross Total', 0)
            try:
                gross = float(gross) if pd.notna(gross) else 0.0
            except: gross = 0.0
            
            if gross <= 0: continue
            
            tax = get_taxes(row)
            
            # Assume gross total is tax inclusive if we're adding tax
            # Calculation: Base = Gross / (1 + TaxRate)
            # TaxRate for 18% is 0.18
            base_price = gross / 1.18
            
            move = env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'invoice_date': date,
                'date': date,
                'ref': ref,
                'journal_id': journal.id,
                'invoice_line_ids': [(0, 0, {
                    'name': 'Sales (Migration)',
                    'quantity': 1,
                    'price_unit': base_price,
                    'tax_ids': [(6, 0, [tax.id])],
                    'account_id': account_income.id,
                })],
            })
            
            try:
                move.action_post()
            except:
                pass
                
            created_count += 1
            if created_count % 50 == 0:
                print(f"  Processed {created_count} sales invoices...")
                env.cr.commit()

        except Exception as e:
            print(f"Error on row {idx}: {e}")
            env.cr.rollback()

    env.cr.commit()
    print(f"Migration Complete. Created {created_count} sales invoices.")

migrate_final_sales()
