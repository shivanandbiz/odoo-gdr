{
    'name': 'Profit and Loss Excel Report',
    "version": "19.0.1.0.0",
    'category': 'Accounting/Reporting',
    'summary': 'Export Profit & Loss to Excel',
    'description': """
        This module provides a wizard to generate a Profit and Loss Report in Excel format.
        It calculates Income and Expenses over a specified date range.
    """,
    'author': 'Antigravity',
    'depends': ['account', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/profit_loss_report_wizard_views.xml',
        'report/report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
