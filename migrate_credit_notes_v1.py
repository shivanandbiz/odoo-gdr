
import pandas as pd
from datetime import datetime

def get_partner_intelligent(env, name):
    name = str(name).strip()
    if not name or name.lower() == 'nan': return False
    partner = env['res.partner'].search([('name', '=ilike', name)], limit=1)
    if not partner:
        clean_name = name.replace('PVT LTD', '').replace('PRIVATE LIMITED', '').replace('Ltd', '').replace('Pvt', '').strip()
        partner = env['res.partner'].search([('name', 'ilike', clean_name)], limit=1)
    return partner

def migrate_credit_notes(env):
    file_path = '/home/biz/GDR_Original_Data/Final Data/credit_note_register_2025_2026.xlsx'
    df = pd.read_excel(file_path, sheet_name='Sheet1', header=8)
    df = df[pd.to_datetime(df['Date'], errors='coerce').notna()]
    
    print(f"Total Credit Notes to process: {len(df)}")
    
    tax_18 = env['account.tax'].search([('name', 'ilike', '18%'), ('type_tax_use', '=', 'sale')], limit=1)
    sales_account = env['account.account'].search([('account_type', '=', 'income'), ('name', 'ilike', 'Sales')], limit=1)
    if not sales_account:
        sales_account = env['account.account'].search([('account_type', '=', 'income')], limit=1)

    count = 0
    for idx, row in df.iterrows():
        try:
            dt_str = pd.to_datetime(row['Date']).strftime('%Y-%m-%d')
            particulars_name = str(row['Particulars']).strip()
            gross_total = float(row['Gross Total'] or 0)
            voucher_ref = str(row['Voucher Ref. No.']).strip() if 'Voucher Ref. No.' in row and pd.notna(row['Voucher Ref. No.']) else f"CN/{idx}"
            
            if gross_total <= 0: continue
            
            partner = get_partner_intelligent(env, particulars_name)
            if not partner:
                print(f"Partner not found: {particulars_name}. Creating...")
                partner = env['res.partner'].create({'name': particulars_name, 'customer_rank': 1})
            
            ref = f"CRN/25-26/{idx}"
            if env['account.move'].search_count([('ref', '=', ref)]):
                continue
            
            # Use out_refund move_type for Credit Notes
            move = env['account.move'].create({
                'move_type': 'out_refund',
                'partner_id': partner.id,
                'date': dt_str,
                'invoice_date': dt_str,
                'ref': ref,
                'invoice_line_ids': [
                    (0, 0, {
                        'name': f"Credit Note: {voucher_ref}",
                        'quantity': 1,
                        'price_unit': gross_total / 1.18 if pd.notna(row.get('IGST@18')) and row['IGST@18'] != 0 else gross_total,
                        'account_id': sales_account.id,
                        'tax_ids': [(6, 0, [tax_18.id])] if pd.notna(row.get('IGST@18')) and row['IGST@18'] != 0 and tax_18 else [],
                    })
                ]
            })
            
            # Adjust price if tax calculation results in different total
            # Actually Odoo handles taxes automatically. 
            # If the Gross Total in excel includes tax, we back-calculate as above.
            
            move.action_post()
            count += 1
            print(f"Migrated Credit Note: {ref} for {partner.name} - Amount: {gross_total}")
            
            # Reconcile with any open invoices
            receivable_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
            if receivable_line:
                open_inv_lines = env['account.move.line'].search([
                    ('partner_id', '=', partner.id),
                    ('account_id', '=', receivable_line.account_id.id),
                    ('reconciled', '=', False),
                    ('move_id.move_type', '=', 'out_invoice'),
                    ('debit', '>', 0)
                ], order='date asc')
                if open_inv_lines:
                    (receivable_line | open_inv_lines).reconcile()
                    print(f"Reconciled {ref} with open invoices.")

        except Exception as e:
            print(f"Error at idx {idx}: {e}")
            env.cr.rollback()

    env.cr.commit()
    print(f"FINISH: Migrated {count} credit notes.")

if __name__ == "__main__":
    migrate_credit_notes(env)
