{
    'name': 'GSTR-1 Report',
    "version": "19.0.1.0.0",
    'category': 'Accounting/Localizations',
    'summary': 'Export GSTR-1 Return to Excel',
    'description': """
        This module provides a wizard to generate the GSTR-1 Outward Supplies Return in Excel format.
        It generates tabs for B2B, B2C Small, Exports, and Credit/Debit Notes for Registered users.
    """,
    'author': 'Antigravity',
    'depends': ['account', 'l10n_in', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/gstr1_report_wizard_views.xml',
        'report/report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
