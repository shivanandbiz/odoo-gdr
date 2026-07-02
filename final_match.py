# final_match.py
ca_types = ['asset_current', 'asset_cash', 'asset_receivable']
cl_types = ['liability_current', 'liability_payable']

ca = sum(env['account.move.line'].search([('account_id.account_type', 'in', ca_types)]).mapped(lambda l: l.debit - l.credit))
cl = sum(env['account.move.line'].search([('account_id.account_type', 'in', cl_types)]).mapped(lambda l: l.credit - l.debit))

print(f"Odoo Current Assets: {ca}")
print(f"Odoo Current Liabilities: {cl}")
