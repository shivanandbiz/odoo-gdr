# reconcile_everything.py
from odoo import api, SUPERUSER_ID

def reconcile_all():
    # 1. Reconcile Receivables (Customers)
    partners = env['res.partner'].search([])
    for partner in partners:
        # Find all open receivable lines
        lines = env['account.move.line'].search([
            ('partner_id', '=', partner.id),
            ('account_type', '=', 'asset_receivable'),
            ('reconciled', '=', False),
            ('move_id.state', '=', 'posted')
        ], order='date asc, id asc')
        
        if len(lines) > 1:
            debits = lines.filtered(lambda l: l.debit > 0)
            credits = lines.filtered(lambda l: l.credit > 0)
            if debits and credits:
                print(f"Reconciling Customer: {partner.name} ({len(debits)} Inv, {len(credits)} Pymt)")
                (debits | credits).reconcile()

    # 2. Reconcile Payables (Suppliers)
    for partner in partners:
        lines = env['account.move.line'].search([
            ('partner_id', '=', partner.id),
            ('account_type', '=', 'liability_payable'),
            ('reconciled', '=', False),
            ('move_id.state', '=', 'posted')
        ], order='date asc, id asc')
        
        if len(lines) > 1:
            debits = lines.filtered(lambda l: l.debit > 0)
            credits = lines.filtered(lambda l: l.credit > 0)
            if debits and credits:
                print(f"Reconciling Supplier: {partner.name} ({len(debits)} Pymt, {len(credits)} Bill)")
                (debits | credits).reconcile()

reconcile_all()
