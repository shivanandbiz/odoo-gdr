
# Setup Company Details
company = env['res.company'].search([], limit=1)
if company:
    # Update Company
    company.write({
        'name': 'GDR Mektek Pvt.Ltd',
        'street': "KT.NO.182, Block 'C' GDR Tech Ville,",
        'street2': "30th KM Bangalore-Mysore Highway, Ketaganahalli, Ramanagara District",
        'city': 'Bidadi',
        'zip': '562109',
        'phone': '9740250192',
        'email': 'marketing@gdrmektek.com',
        'website': 'http://www.gdrmektek.com',
        'vat': '29AACCG6108L1ZE',
    })
    
    # Partner details (the partner record linked to company)
    company.partner_id.write({
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
    })

    # Set PAN if the field exists (usually via l10n_in)
    if 'l10n_in_pan' in company._fields:
        company.write({'l10n_in_pan': 'AACCG6108L'})

    # Set Country and State
    country = env['res.country'].search([('code', '=', 'IN')], limit=1)
    if country:
        state = env['res.country.state'].search([('name', '=ilike', 'Karnataka'), ('country_id', '=', country.id)], limit=1)
        company.write({'country_id': country.id})
        company.partner_id.write({'country_id': country.id})
        if state:
            company.write({'state_id': state.id})
            company.partner_id.write({'state_id': state.id})

    # Set Currency to INR
    inr = env['res.currency'].search([('name', '=', 'INR')], limit=1)
    if inr:
        if not inr.active:
            inr.active = True
        company.write({'currency_id': inr.id})

    print(f"Company '{company.name}' updated successfully.")

    # Configure Indian Chart of Accounts if not already done
    # Search for the chart template
    chart_template = env['account.chart.template'].search([('name', '=ilike', 'Indian Chart of Accounts%')], limit=1)
    if chart_template:
        # Check if already loaded
        if not company.chart_template_id:
            try:
                chart_template.try_loading(company)
                print("Indian Chart of Accounts loaded.")
            except Exception as e:
                print(f"Could not load Chart of Accounts: {e}")
        else:
            print(f"Chart of Accounts already set to: {company.chart_template_id.name}")

env.cr.commit()
