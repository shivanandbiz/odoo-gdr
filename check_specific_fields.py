
cf = env['res.company']._fields
pf = env['res.partner']._fields
print(f"Company has vat: {'vat' in cf}")
print(f"Company has l10n_in_pan: {'l10n_in_pan' in cf}")
print(f"Partner has mobile: {'mobile' in pf}")
print(f"Partner has l10n_in_pan: {'l10n_in_pan' in pf}")
