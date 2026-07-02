
# Final Company Setup
company = env['res.company'].search([], limit=1)
if company:
    vals = {
        'name': 'GDR Mektek Pvt.Ltd',
        'street': "KT.NO.182, Block 'C' GDR Tech Ville,",
        'street2': "30th KM Bangalore-Mysore Highway, Ketaganahalli, Ramanagara District",
        'city': 'Bidadi',
        'zip': '562109',
        'phone': '9740250192',
        'email': 'marketing@gdrmektek.com',
        'website': 'http://www.gdrmektek.com',
        'vat': '29AACCG6108L1ZE',
    }
    # Only write fields that exist
    company.write({k: v for k, v in vals.items() if k in company._fields})

    partner_vals = {
        'name': 'GDR Mektek Pvt.Ltd',
        'street': "KT.NO.182, Block 'C' GDR Tech Ville,",
        'street2': "30th KM Bangalore-Mysore Highway, Ketaganahalli, Ramanagara District",
        'city': 'Bidadi',
        'zip': '562109',
        'phone': '9740250192',
        'mobile': '7044616257',
        'email': 'marketing@gdrmektek.com',
        'website': 'http://www.gdrmektek.com',
        'vat': '29AACCG6108L1ZE',
        'is_company': True,
    }
    company.partner_id.write({k: v for k, v in partner_vals.items() if k in company.partner_id._fields})

    # Country/State
    country = env['res.country'].search([('code', '=', 'IN')], limit=1)
    if country:
        state = env['res.country.state'].search([('name', '=ilike', 'Karnataka'), ('country_id', '=', country.id)], limit=1)
        company.write({'country_id': country.id})
        company.partner_id.write({'country_id': country.id})
        if state:
            company.write({'state_id': state.id})
            company.partner_id.write({'state_id': state.id})

    # INR Currency
    inr = env['res.currency'].search([('name', '=', 'INR')], limit=1)
    if inr:
        if not inr.active: inr.active = True
        company.write({'currency_id': inr.id})

    # PAN
    if 'l10n_in_pan' in company._fields:
        company.write({'l10n_in_pan': 'AACCG6108L'})

    print(f"Company '{company.name}' detailed setup finished.")

env.cr.commit()
