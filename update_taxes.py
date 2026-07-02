tax_sale = env['account.tax'].browse(1)
if tax_sale.exists():
    tax_sale.write({'amount': 18.0, 'name': '18%'})
else:
    tax_sale = env['account.tax'].search([('type_tax_use', '=', 'sale'), ('amount', '=', 18.0)], limit=1)
    if not tax_sale:
        tax_sale = env['account.tax'].create({'name': '18%', 'amount': 18.0, 'type_tax_use': 'sale'})

tax_purchase = env['account.tax'].browse(2)
if tax_purchase.exists():
    tax_purchase.write({'amount': 18.0, 'name': '18%'})
else:
    tax_purchase = env['account.tax'].search([('type_tax_use', '=', 'purchase'), ('amount', '=', 18.0)], limit=1)
    if not tax_purchase:
        tax_purchase = env['account.tax'].create({'name': '18%', 'amount': 18.0, 'type_tax_use': 'purchase'})

# Ensure all products have these default taxes
products = env['product.template'].search([])
# Write in batches to avoid taking too much memory or time, actually search is fast and write on recordset is optimized.
products.write({
    'taxes_id': [(6, 0, [tax_sale.id])],
    'supplier_taxes_id': [(6, 0, [tax_purchase.id])]
})
env.cr.commit()

# Also update the company default taxes so new products get them automatically
company = env.user.company_id
company.write({
    'account_sale_tax_id': tax_sale.id,
    'account_purchase_tax_id': tax_purchase.id
})
env.cr.commit()

print(f"Updated {len(products)} products to use 18% Customer and Vendor Taxes.")
