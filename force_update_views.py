
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.tools import config
import os

def force_update_view():
    config.parse_config(['-c', 'debian/odoo.conf'])
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Path to the file
        file_path = '/home/ubuntu/odoo-gdr/addons/account/views/report_invoice.xml'
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Extract the template with id="report_invoice_document"
        import xml.etree.ElementTree as ET
        tree = ET.fromstring(content)
        template = tree.find(".//template[@id='report_invoice_document']")
        if template is not None:
            arch = ET.tostring(template, encoding='unicode')
            # Remove the <template ...> and </template> tags to get just the inner content
            # or better, just find the view and update its arch_db
            view = env['ir.ui.view'].search([('key', '=', 'account.report_invoice_document')], limit=1)
            if view:
                # We need to be careful with the XML format. 
                # Actually, Odoo's -u command should work if we reset the 'customized' flag.
                print(f"RESETTING CUSTOMIZED FLAG FOR VIEW {view.id}")
                cr.execute("UPDATE ir_ui_view SET arch_fs = 'account/views/report_invoice.xml' WHERE id = %s", (view.id,))
                # Also delete any coco/studio overrides if they exist
                cr.execute("DELETE FROM ir_ui_view WHERE inherit_id = %s AND (key LIKE 'studio%%' OR name LIKE 'Studio%%')", (view.id,))
        
        # Same for report_payment_receipt_templates.xml
        view_pay = env['ir.ui.view'].search([('key', '=', 'account.report_payment_receipt_document')], limit=1)
        if view_pay:
            print(f"RESETTING CUSTOMIZED FLAG FOR VIEW {view_pay.id}")
            cr.execute("UPDATE ir_ui_view SET arch_fs = 'account/views/report_payment_receipt_templates.xml' WHERE id = %s", (view_pay.id,))

if __name__ == "__main__":
    force_update_view()
