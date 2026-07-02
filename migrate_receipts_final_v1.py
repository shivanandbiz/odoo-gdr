
import pandas as pd
import odoo
from odoo import api, SUPERUSER_ID
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger('migrate_receipts')

EXCEL_PATH = '/home/biz/GDR_Original_Data/Final Data/Final_recipt_register_2025_2026.xlsx'
ODOO_CONF = 'odoo.conf'

# Journal Mapping based on Excel Columns
JOURNAL_MAP = {
    'HDFC C/A 50200024612749': 'HC5',
    'Kotak -3545975369': 'K-',
    'Gkp Current A/c': 'BNK1', # Assumption
    # Add more if needed
}

def migrate_receipts():
    # Load Excel
    df = pd.read_excel(EXCEL_PATH, header=8)
    df = df.dropna(subset=['Particulars'])
    
    # Initialize Odoo
    odoo.tools.config.parse(['-c', ODOO_CONF])
    db_name = odoo.tools.config['db_name'] or 'odoo'
    registry = odoo.registry(db_name)
    
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        for index, row in df.iterrows():
            partner_name = str(row['Particulars']).strip()
            amount = float(row['Gross Total'])
            date = str(row['Date']).split(' ')[0]
            ref = str(row['Voucher Ref. No.']) if pd.notna(row['Voucher Ref. No.']) else ''
            narration = str(row['Narration']) if pd.notna(row['Narration']) else ''
            
            _logger.info(f"Processing Receipt: {partner_name} - {amount} on {date}")
            
            # 1. Find Partner
            partner = env['res.partner'].search([('name', '=', partner_name)], limit=1)
            if not partner:
                partner = env['res.partner'].search([('name', 'ilike', partner_name)], limit=1)
            
            if not partner:
                _logger.warning(f"Partner NOT FOUND: {partner_name}. Skipping row {index}")
                continue
                
            # 2. Determine Journal
            # Find which bank column has the value
            journal_code = 'BNK1' # Default
            for col in JOURNAL_MAP.keys():
                if col in row and pd.notna(row[col]) and row[col] != 0:
                    journal_code = JOURNAL_MAP[col]
                    break
            
            journal = env['account.journal'].search([('code', '=', journal_code)], limit=1)
            if not journal:
                _logger.error(f"Journal NOT FOUND for code {journal_code}. Skipping.")
                continue

            # 3. Create Payment
            payment_vals = {
                'date': date,
                'amount': amount,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': partner.id,
                'journal_id': journal.id,
                'ref': f"{ref} {narration}".strip(),
            }
            
            try:
                payment = env['account.payment'].create(payment_vals)
                payment.action_post()
                _logger.info(f"Created Payment: {payment.name} for {partner.name}")
                
                # 4. Attempt Reconciliation
                # Look for open invoices for this partner
                invoices = env['account.move'].search([
                    ('partner_id', '=', partner.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ['not_paid', 'partial'])
                ], order='invoice_date asc')
                
                remaining_amount = amount
                for inv in invoices:
                    if remaining_amount <= 0:
                        break
                        
                    # Logic to reconcile
                    # This is complex in Odoo 15+ (need to use js_assign_outstanding_line)
                    # For now, we created the payment. Odoo will show it as an outstanding credit.
                    pass
                    
            except Exception as e:
                _logger.error(f"Error creating payment for {partner_name}: {e}")
                cr.rollback()
                continue
                
        cr.commit()

if __name__ == '__main__':
    migrate_receipts()
