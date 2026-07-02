all_bills = env['account.move'].search([('move_type', '=', 'in_invoice'), ('state', '=', 'posted')])
monthly = {}
for m in all_bills:
    my = m.date.strftime('%Y-%m')
    monthly[my] = monthly.get(my, 0) + m.amount_total

target = {
    '2025-04': 4965142.20, '2025-05': 5935852.36, '2025-06': 5902935.38,
    '2025-07': 5832890.98, '2025-08': 2706354.30, '2025-09': 3742037.02,
    '2025-10': 5164669.18, '2025-11': 4396926.92, '2025-12': 4792170.86,
    '2026-01': 7199291.74, '2026-02': 9630540.24, '2026-03': 30054329.14
}

print("\nFinal Odoo Monthly Audit:")
for m in sorted(target.keys()):
    act = monthly.get(m, 0)
    print(f"{m}: Act={act:12.2f} | Tgt={target[m]:12.2f} | Diff={act-target[m]:12.2f}")
