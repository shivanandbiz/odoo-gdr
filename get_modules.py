
import os
modules = env['ir.module.module'].search([('state', '=', 'installed')]).mapped('name')
with open('/home/biz/odoo/module_output.txt', 'w') as f:
    f.write("\n".join(sorted(modules)))
