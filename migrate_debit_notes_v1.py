
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

def get_or_create_account(env, name):
    name = str(name).strip()
    if not name or name.lower() == 'nan': return False
    acc = env['account.account'].search([('name', '=', name)], limit=1)
    if not acc:
        acc = env['account.account'].search([('name', '=ilike', name)], limit=1)
    if not acc:
        if 'IGST' in name or 'CGST' in name or 'SGST' in name:
            acc = env['account.account'].search([('name', 'ilike', name[:4])], limit=1)
        if not acc:
            acc = env['account.account'].search([('account_type', '=', 'expense')], limit=1)
    return acc

def migrate_debit_notes(env):
    file_path = '/home/biz/GDR_Original_Data/Final Data/Debit_Note_Register_2025_2026.xlsx'
    df = pd.read_excel(file_path, sheet_name='Sheet1', header=8)
    df = df[pd.to_datetime(df['Date'], errors='coerce').notna()]
    
    print(f"Total Debit Notes to process: {len(df)}")
    
    count = 0
    account_cols = ['PURCHASE INTERSTATE', 'IGST@18', 'INTERSTATE PURCHASE @18%', 'LOCAL PURCHASE GST 18%', 'CGST @ 9%', 'SGST@ 9%']

    for idx, row in df.iterrows():
        try:
            dt_str = pd.to_datetime(row['Date']).strftime('%Y-%m-%d')
            particulars_name = str(row['Particulars']).strip()
            gross_total = float(row['Gross Total'] or 0)
            
            if gross_total <= 0: continue
            
            partner = get_partner_intelligent(env, particulars_name)
            if not partner:
                print(f"Partner not found: {particulars_name}. Creating...")
                partner = env['res.partner'].create({'name': particulars_name, 'supplier_rank': 1})
            
            ref = f"DBN/25-26/{idx}"
            if env['account.move'].search_count([('ref', '=', ref)]):
                continue
            
            # Use in_refund move_type for Vendor Debit Notes (reversals of bills)
            invoice_lines = []
            for col in account_cols:
                if col in row and pd.notna(row[col]) and float(row[col]) != 0:
                    val = abs(float(row[col]))
                    acc = get_or_create_account(env, col)
                    invoice_lines.append((0, 0, {
                        'name': f"Debit Note: {col}",
                        'quantity': 1,
                        'price_unit': val,
                        'account_id': acc.id,
                    }))
            
            if not invoice_lines:
                # Fallback to gross total if no breakdown columns have values
                acc = env['account.account'].search([('account_type', '=', 'expense')], limit=1)
                invoice_lines.append((0, 0, {
                    'name': f"Debit Note: {particulars_name}",
                    'quantity': 1,
                    'price_unit': gross_total,
                    'account_id': acc.id,
                }))

            move = env['account.move'].create({
                'move_type': 'in_refund',
                'partner_id': partner.id,
                'date': dt_str,
                'invoice_date': dt_str,
                'ref': ref,
                'invoice_line_ids': invoice_lines
            })
            
            move.action_post()
            count += 1
            print(f"Migrated Debit Note: {ref} for {partner.name} - Amount: {gross_total}")
            
            # Reconcile with any open vendor bills
            payable_line = move.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable')
            if payable_line:
                open_bill_lines = env['account.move.line'].search([
                    ('partner_id', '=', partner.id),
                    ('account_id', '=', payable_line.account_id.id),
                    ('reconciled', '=', False),
                    ('move_id.move_type', '=', 'in_invoice'),
                    ('credit', '>', 0)
                ], order='date asc')
                if open_bill_lines:
                    (payable_line | open_bill_lines).reconcile()
                    print(f"Reconciled {ref} with open bills.")

        except Exception as e:
            print(f"Error at idx {idx}: {e}")
            env.cr.rollback()

    env.cr.commit()
    print(f"FINISH: Migrated {count} debit notes.")

if __name__ == "__main__":
    migrate_debit_notes(env)
