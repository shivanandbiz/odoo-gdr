
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_views():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        base_view = env.ref('account.view_account_move_reversal', raise_if_not_found=False)
        if base_view:
            print(f"Base View ID: {base_view.id}")
            inheriting_views = env['ir.ui.view'].search([('inherit_id', '=', base_view.id)])
            for view in inheriting_views:
                print(f"Inheriting View: {view.name} (ID: {view.id}) from module {view.arch_fs or 'unknown'}")
                # print(view.arch)
        else:
            print("Base view NOT FOUND")

if __name__ == "__main__":
    check_views()
