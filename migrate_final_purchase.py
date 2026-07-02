
import pandas as pd
import math
from datetime import datetime

def migrate_final_purchase():
    file_path = "/home/biz/GDR_Original_Data/Final Data/Final_purchase_invoice.xlsx"
    print(f"Reading {file_path} ...")
    
    # Read the file starting from the correct header row (index 2 based on previous inspection)
    df = pd.read_excel(file_path, header=2)
    
    # Remove rows without Date or Particulars
    df = df[df['Date'].notna() & df['Particulars'].notna()].copy()
    # Filter out footer typical of Tally exports
    df = df[~df['Particulars'].str.contains('Grand Total', na=False)]
    
    print(f"Found {len(df)} rows to process.")

    # 1. DELETE existing vendor bills (as the target is a clean migration)
    print("Deleting existing vendor bills...")
    existing = env['account.move'].search([('move_type', '=', 'in_invoice')])
    if existing:
        existing.button_draft()
        existing.unlink()
        env.cr.commit()
    print("  Cleaned existing.")

    # Caches
    partner_cache = {}
    product_cache = {}
    tax_cache = {}
    
    account_expense = env['account.account'].search([('account_type', '=', 'expense')], limit=1)
    journal = env['account.journal'].search([('type', '=', 'purchase')], limit=1)

    def get_partner(name):
        name = str(name).strip()
        if name not in partner_cache:
            p = env['res.partner'].search([('name', '=', name)], limit=1)
            if not p:
                p = env['res.partner'].create({'name': name, 'supplier_rank': 1, 'is_company': True})
            partner_cache[name] = p
        return partner_cache[name]

    def get_product(name):
        name = str(name).strip()
        if name not in product_cache:
            p = env['product.product'].search([('name', '=', name)], limit=1)
            if not p:
                p = env['product.product'].create({
                    'name': name,
                    'type': 'service',  # Summary items are better as service
                    'purchase_ok': True,
                })
            product_cache[name] = p
        return product_cache[name]

    def get_taxes(col_name):
        # Map column names to taxes
        if col_name not in tax_cache:
            taxes = env['account.tax']
            amount = 0
            if '18%' in col_name: amount = 18
            elif '28%' in col_name: amount = 28
            elif '12%' in col_name: amount = 12
            elif '5%' in col_name: amount = 5
            
            if amount > 0:
                taxes = env['account.tax'].search([('amount', '=', amount), ('type_tax_use', '=', 'purchase')], limit=1)
                if not taxes:
                    taxes = env['account.tax'].create({
                        'name': f'GST {amount}%',
                        'amount': amount,
                        'type_tax_use': 'purchase',
                        'country_id': env.company.account_fiscal_country_id.id or env.company.country_id.id,
                    })
            tax_cache[col_name] = taxes
        return tax_cache[col_name]

    # Columns that represent line items (taxable values)
    taxable_columns = [
        'LOCAL PURCHASE GST 18%', 'Interstate Purchases Gst @28%', 'INTERSTATE PURCHASE @18%',
        'Local Purchases Gst @5%', 'GST PURCHASE @12%', 'Local Purchase Gst @5%', 'LOCAL PURCHASE GST @28 %'
    ]
    
    # Other cost columns
    other_columns = ['Rounded Off', 'Discount Received']

    created_count = 0
    for idx, row in df.iterrows():
        try:
            date = row['Date']
            if pd.isna(date): continue
            if isinstance(date, str):
                date = datetime.strptime(date, '%Y-%m-%d').date()
            
            partner = get_partner(row['Particulars'])
            ref = str(row['Supplier Invoice No.']).strip() if pd.notna(row['Supplier Invoice No.']) else f"MIG_{idx}"
            
            line_ids = []
            
            # Process taxable columns as products
            for col in taxable_columns:
                val = row.get(col, 0)
                if pd.notna(val) and float(val) != 0:
                    taxes = get_taxes(col)
                    product = get_product(col)
                    line_ids.append((0, 0, {
                        'product_id': product.id,
                        'name': col,
                        'quantity': 1,
                        'price_unit': float(val),
                        'tax_ids': [(6, 0, taxes.ids)],
                        'account_id': account_expense.id,
                    }))
            
            # If no taxable lines, use Gross Total as a single generic line
            if not line_ids:
                gross = row.get('Gross Total', 0)
                if pd.notna(gross) and float(gross) != 0:
                    product = get_product("Purchase (Migration)")
                    line_ids.append((0, 0, {
                        'product_id': product.id,
                        'name': "Purchase (Migration)",
                        'quantity': 1,
                        'price_unit': float(gross),
                        'account_id': account_expense.id,
                    }))

            # Handle Rounded Off / Discount as separate lines if non-zero
            for col in other_columns:
                val = row.get(col, 0)
                if pd.notna(val) and float(val) != 0:
                    product = get_product(col)
                    line_ids.append((0, 0, {
                        'product_id': product.id,
                        'name': col,
                        'quantity': 1,
                        'price_unit': float(val),
                        'account_id': account_expense.id,
                    }))

            if not line_ids:
                continue

            move = env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': partner.id,
                'invoice_date': date,
                'date': date,
                'ref': ref,
                'journal_id': journal.id,
                'invoice_line_ids': line_ids,
            })
            
            # Try to post
            try:
                move.action_post()
            except:
                pass
                
            created_count += 1
            if created_count % 50 == 0:
                print(f"  Processed {created_count} invoices...")
                env.cr.commit()

        except Exception as e:
            print(f"Error on row {idx}: {e}")
            env.cr.rollback()

    env.cr.commit()
    print(f"Migration Complete. Created {created_count} bills.")

migrate_final_purchase()
