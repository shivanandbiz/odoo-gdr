# Check if we can link move and payment
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
print(f"Created Move: {move.id}")

payment = env['account.payment'].create({
    'payment_type': 'outbound',
    'partner_type': 'supplier',
    'partner_id': partner.id,
    'amount': 100,
    'journal_id': journal.id,
    'date': '2025-04-01',
    'state': 'draft',
})
print(f"Created Payment: {payment.id}")

env.cr.execute("UPDATE account_payment SET move_id = %s WHERE id = %s", (move.id, payment.id))
env.cr.execute("UPDATE account_move SET payment_id = %s WHERE id = %s", (payment.id, move.id))
payment.invalidate_recordset()
move.invalidate_recordset()

try:
    payment.state = 'in_process'
    print("Success setting state to in_process")
except Exception as e:
    print(f"Error setting state: {e}")

env.cr.rollback() # Don't commit test data
