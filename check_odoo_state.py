print("--- JOURNALS ---")
for j in env['account.journal'].search([]):
    print(f"{j.name} ({j.code}) type: {j.type}")
print("--- BANKS ---")
for j in env['account.journal'].search([('type', '=', 'bank')]):
    print(f"Bank Journal: {j.name}")
