
fields = env['res.partner']._fields
for f in ['mobile', 'vat', 'phone', 'email', 'street', 'city', 'zip']:
    print(f"{f}: {f in fields}")
