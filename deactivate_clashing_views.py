
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def deactivate_clashing_views():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        # Find views from account_india_credit_debit_bridge using ir.model.data
        data_records = env['ir.model.data'].search([
            ('module', '=', 'account_india_credit_debit_bridge'),
            ('model', '=', 'ir.ui.view')
        ])
        for record in data_records:
            view = env['ir.ui.view'].browse(record.res_id)
            if view.exists():
                print(f"Deactivating view: {view.name} (ID: {view.id}, XML ID: {record.module}.{record.name})")
                view.active = False
        cr.commit()
        print("Clashing views deactivated successfully.")

if __name__ == "__main__":
    deactivate_clashing_views()
