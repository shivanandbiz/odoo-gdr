# count_bills.py
print(f"Bills: {env['account.move'].search_count([('move_type', '=', 'in_invoice')])}")
