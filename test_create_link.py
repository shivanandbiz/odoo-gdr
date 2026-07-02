journal = env['account.journal'].search([('type', '=', 'bank')], limit=1)
partner = env['res.partner'].search([], limit=1)
acc = partner.property_account_payable_id or journal.default_account_id

move = env['account.move'].create({
    'move_type': 'entry',
    'date': '2025-04-01',
    'journal_id': journal.id,
    'line_ids': [
        (0, 0, {'account_id': acc.id, 'debit': 100, 'credit': 0, 'partner_id': partner.id}),
        (0, 0, {'account_id': journal.default_account_id.id, 'debit': 0, 'credit': 100}),
    ]
})
move.action_post()

try:
    payment = env['account.payment'].create({
        'payment_type': 'outbound',
        'partner_type': 'supplier',
        'partner_id': partner.id,
        'amount': 100,
        'journal_id': journal.id,
        'date': '2025-04-01',
        'move_id': move.id,
        'state': 'in_process',
    })
    print(f"Success! Payment: {payment.id}, Move: {payment.move_id.id}")
except Exception as e:
    print(f"Error: {e}")

env.cr.rollback()
