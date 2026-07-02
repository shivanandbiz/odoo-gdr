
import odoo
from odoo import api, SUPERUSER_ID

def audit():
    common = odoo.xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/common')
    uid = common.authenticate('odoo', 'admin', 'admin', {}) # Assuming default credentials from context
    models = odoo.xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/object')

    # Count Customer Payments
    payments_count = models.execute_kw('odoo', uid, 'admin', 'account.payment', 'search_count', [[('partner_type', '=', 'customer'), ('state', '!=', 'draft')]])
    # Count Customer Invoices
    invoices_count = models.execute_kw('odoo', uid, 'admin', 'account.move', 'search_count', [[('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]])
    # Count Reconciled Invoices
    paid_invoices_count = models.execute_kw('odoo', uid, 'admin', 'account.move', 'search_count', [[('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('payment_state', 'in', ('paid', 'in_payment'))]])

    print(f"Total Posted Customer Payments: {payments_count}")
    print(f"Total Posted Customer Invoices: {invoices_count}")
    print(f"Total Paid Customer Invoices: {paid_invoices_count}")

if __name__ == "__main__":
    # Try local shell approach if possible, otherwise use python script with odoo bin
    print("Running audit...")
    # Since I don't know the exact db name, I'll check common ones. 
    # Usually it's 'gdr_final' or 'odoo' based on previous context.
