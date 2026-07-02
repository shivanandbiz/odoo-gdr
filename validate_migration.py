# validate_migration.py
moves = env['account.move'].search([('move_type', '=', 'in_invoice')])
stats = {}

for m in moves:
    month = m.date.strftime('%m-%B')
    if month not in stats: stats[month] = 0
    stats[month] += m.amount_untaxed

print("\n--- ODOO PURCHASE REGISTER BY MONTH ---")
for m in sorted(stats.keys()):
    print(f"{m}: {stats[m]:,.2f}")

grand_total = sum(stats.values())
print(f"GRAND TOTAL: {grand_total:,.2f}")
print(f"TARGET TOTAL: 90,323,140.32")
print(f"VARIANCE: {grand_total - 90323140.32:,.2f}")
