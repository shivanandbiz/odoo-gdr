
import odoo
from odoo import api, SUPERUSER_ID

def reconcile_all(env):
    print("Starting auto-reconciliation...")
    partners = env['res.partner'].search([('customer_rank', '>', 0)])
    total_reconciled = 0
    
    for partner in partners:
        # Find all open receivable lines for this partner
        # We look for lines in asset_receivable accounts that are not reconciled
        lines = env['account.move.line'].search([
            ('partner_id', '=', partner.id),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('reconciled', '=', False),
            ('move_id.state', '=', 'posted')
        ], order='date asc, id asc')
        
        if len(lines) > 1:
            debit_lines = lines.filtered(lambda l: l.debit > 0)
            credit_lines = lines.filtered(lambda l: l.credit > 0)
            
            if debit_lines and credit_lines:
                print(f"Reconciling {partner.name}: {len(debit_lines)} debits, {len(credit_lines)} credits")
                try:
                    (debit_lines | credit_lines).reconcile()
                    total_reconciled += 1
                except Exception as e:
                    print(f"Error reconciling {partner.name}: {e}")
                    env.cr.rollback()
                    continue
        
        # Commit every few partners
        if total_reconciled % 10 == 0:
            env.cr.commit()

    env.cr.commit()
    print(f"Finished reconciliation for {total_reconciled} partners.")

if __name__ == "__main__":
    reconcile_all(env)
