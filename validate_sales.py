# validate_sales.py
moves = env['account.move'].search([('move_type', '=', 'out_invoice')], limit=5)
for m in moves:
    print(f"\nInvoice: {m.ref} | Customer: {m.partner_id.name} | Date: {m.invoice_date} | Total: {m.amount_total}")
    for line in m.invoice_line_ids:
        tax_names = ", ".join(line.tax_ids.mapped('name'))
        print(f"  - Line: {line.product_id.name} | Qty: {line.quantity} | Total: {line.price_subtotal} | Taxes: {tax_names}")

# Total count check
total = env['account.move'].search_count([('move_type', '=', 'out_invoice')])
print(f"\nTotal Odoo Sales Invoices: {total}")
