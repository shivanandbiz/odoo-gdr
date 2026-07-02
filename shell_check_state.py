modules = env['ir.module.module'].search([('name', 'in', ['hr', 'payroll'])])
for mod in modules:
    print(f"Module '{mod.name}' state: {mod.state}")
