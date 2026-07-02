# Update app list
print("Updating module list...")
env['ir.module.module'].update_list()

modules = env['ir.module.module'].search([('name', 'in', ['hr_contract', 'hr'])])
print(f"Found modules: {modules.mapped('name')}")
