print("Stock Module State:", env['ir.module.module'].search([('name', '=', 'stock')]).state)
print("Product Type Selection:", env['product.template']._fields['type'].selection)
