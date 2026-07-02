
vat_to_check = '22AAAGM0289C1ZT'
recs = env['res.partner'].search([('vat', '=', vat_to_check), ('active', '=', True)])
print(f"Details for VAT {vat_to_check}:")
for r in recs:
    print(f"  [{r.id}] Name: '{r.name}' | Parent: '{r.parent_id.name if r.parent_id else 'None'}' | Type: {r.type} | Is Company: {r.is_company}")
