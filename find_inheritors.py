
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.tools import config

def find_inheriting_views():
    config.parse_config(['-c', 'debian/odoo.conf'])
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        # Find ID of account.report_invoice_document
        base_view = env['ir.ui.view'].search([('key', '=', 'account.report_invoice_document')], limit=1)
        if not base_view:
            print("BASE VIEW NOT FOUND")
            return
        
        views = env['ir.ui.view'].search([('inherit_id', '=', base_view.id)])
        print(f"FOUND {len(views)} INHERITING VIEWS")
        for v in views:
            print(f"--- {v.key} ({v.id}) from {v.arch_fs or 'DB'} ---")
            # Print any( if present
            if 'any(' in v.arch_db:
                print("HAS any(")
                for line in v.arch_db.split('\n'):
                    if 'any(' in line:
                        print(line.strip())

if __name__ == "__main__":
    find_inheriting_views()
