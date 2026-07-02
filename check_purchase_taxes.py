# check_purchase_taxes.py
bills = env['account.move'].search([('move_type', '=', 'in_invoice')], limit=10)
for b in bills:
    taxes = ", ".join(b.invoice_line_ids[0].tax_ids.mapped('name'))
    print(f"Bill {b.ref} | Vendor: {b.partner_id.name} | Taxes: [{taxes}]")
