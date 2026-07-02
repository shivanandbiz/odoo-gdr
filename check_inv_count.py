
count = env['account.move'].search_count([('move_type', '=', 'out_invoice')])
print(f"Total Sales Invoices: {count}")
