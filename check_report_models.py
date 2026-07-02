
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_report_models():
    db_name = 'odoo'  # Based on log file
    registry = Registry(db_name)
    
    models_to_check = [
        'account.balance.report',  # Balance Sheet
        'account.common.report',
        'account.report.general.ledger',
        'account.trial.balance',
        'account.tax.report',
        'account.aged.trial.balance',
        'account.print.journal',
        'account.partner.ledger',
        'account.aged.receivable',
        'account.aged.payable',
        'account.daybook.report',
        'account.cashbook.report',
        'account.bankbook.report',
        'account.invoice.report',
        'account.analytic.report',
        'account.budget.report',
    ]
    
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        print(f"{'Model Name':<40} | {'Status':<10}")
        print("-" * 55)
        for model in models_to_check:
            status = "FOUND" if model in env else "MISSING"
            print(f"{model:<40} | {status:<10}")

if __name__ == "__main__":
    check_report_models()
