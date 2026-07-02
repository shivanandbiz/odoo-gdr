journal = env['account.journal'].search([('type', '=', 'bank')], limit=1)
partner = env['res.partner'].search([('supplier_rank', '>', 0)], limit=1)
try:
    payment = env['account.payment'].create({
        'payment_type': 'outbound',
        'partner_type': 'supplier',
        'partner_id': partner.id,
        'amount': 123.45,
        'journal_id': journal.id,
        'date': '2025-04-01',
        'memo': 'TEST_PAYMENT_1',
    })
    payment.action_post()
    print(f"Success! Status: {payment.state}, Move: {payment.move_id.name}")
except Exception as e:
    print(f"Error: {e}")
env.cr.rollback()
