print("--- ACCOUNTS ---")
for a in env['account.account'].search([]):
    print(f"{a.code} {a.name} ({a.account_type})")
