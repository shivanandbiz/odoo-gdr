import odoo
from odoo import api, SUPERUSER_ID

modules_to_install = [
    'mail', 'calendar', 'appointment', 'project_todo', 'sale_management',
    'board', 'documents', 'project', 'purchase',
    'stock', 'mrp', 'quality_control', 'stock_barcode', 'mrp_plm', 'sign',
    'hr', 'hr_attendance', 'hr_recruitment', 'hr_holidays',
    'approvals', 'link_tracker'
]

print("Scanning for modules...")
for m in modules_to_install:
    mod = env['ir.module.module'].search([('name', '=', m)])
    if not mod:
        print(f"Module '{m}' does NOT exist in this Odoo installation (likely Enterprise only or wrong name).")
    elif mod.state == 'uninstalled':
        print(f"Module '{m}' is UNINSTALLED. Queuing setup...")
        mod.button_immediate_install()
        env.cr.commit()
    else:
        print(f"Module '{m}' is already {mod.state}.")

