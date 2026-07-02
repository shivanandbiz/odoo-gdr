
modules = env['ir.module.module'].search([('state', '=', 'installed')]).mapped('name')
print(sorted(modules))
