import pandas as pd
df = pd.read_excel('apr_june_payment.xlsx', header=None)
headers = df.iloc[8].tolist()
accounts_map = {i: str(headers[i]).strip() for i in range(7, len(headers)) if pd.notna(headers[i])}

journal = env['account.journal'].search([('type', '=', 'bank')], limit=1)

for idx, row in df.iloc[9:14].iterrows():
    r = row.tolist()
    amount = float(r[6] or 0)
    part_name = str(r[1])
    
    move = env['account.move'].create({
        'move_type': 'entry',
        'date': '2025-04-01',
        'journal_id': journal.id,
        'line_ids': [
            (0, 0, {'account_id': journal.default_account_id.id, 'debit': amount, 'credit': 0}),
            (0, 0, {'account_id': journal.default_account_id.id, 'debit': 0, 'credit': amount}),
        ]
    })
    move.action_post()
    
    payment = env['account.payment'].create({
        'payment_type': 'outbound',
        'partner_type': 'supplier',
        'partner_id': False,
        'amount': amount,
        'journal_id': journal.id,
        'date': '2025-04-01',
        'move_id': move.id,
        'state': 'in_process',
    })
    print(f"Row {idx} success: {payment.id}")

env.cr.rollback()
