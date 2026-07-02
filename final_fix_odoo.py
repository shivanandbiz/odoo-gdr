# 1. Fix November: add 0.14
print("Fixing November...")
nov_inv = env['account.move'].search([('move_type', '=', 'in_invoice'), ('date', '>=', '2025-11-01'), ('date', '<=', '2025-11-30')], limit=1)
if nov_inv:
    was_posted = nov_inv.state == 'posted'
    if was_posted:
        nov_inv.button_draft()
    
    rounding_acc = env['account.account'].search([('name', 'ilike', 'round')], limit=1)
    
    nov_inv.write({
        'invoice_line_ids': [(0, 0, {
            'name': 'Rounded Off (Manual Adjust)',
            'account_id': rounding_acc.id,
            'quantity': 1,
            'price_unit': 0.14,
            'tax_ids': [(5, 0, 0)]
        })]
    })
    if was_posted:
        nov_inv.action_post()
    print("November fixed (+0.14)")

# 2. Fix January: subtract 136664.49
print("Fixing January...")
jan_inv = env['account.move'].search([('move_type', '=', 'in_invoice'), ('date', '>=', '2026-01-01'), ('date', '<=', '2026-01-31'), ('amount_total', '>', 200000)], limit=1)

if jan_inv:
    was_posted = jan_inv.state == 'posted'
    if was_posted:
        jan_inv.button_draft()
    
    jan_inv.write({
        'invoice_line_ids': [(0, 0, {
            'name': 'Rounded Off (Manual Adjust)',
            'account_id': rounding_acc.id,
            'quantity': 1,
            'price_unit': -136664.49,
            'tax_ids': [(5, 0, 0)]
        })]
    })
    if was_posted:
        jan_inv.action_post()
    print("January fixed (-136664.49)")

env.cr.commit()
print("Done finalizing balances")
