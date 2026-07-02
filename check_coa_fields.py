print("Fields:", list(env['account.chart.template']._fields.keys()))
templates = env['account.chart.template'].search([])
for t in templates:
    # Try to find what identifying field it has
    if hasattr(t, 'name'): print(f"Template Name: {t.name}")
    elif hasattr(t, 'display_name'): print(f"Template Display Name: {t.display_name}")
