{
    'name': 'GSTR-3B Summary Report',
    "version": "19.0.1.0.0",
    'category': 'Accounting/Localizations',
    'summary': 'Export GSTR-3B Summary Return to Excel',
    'description': """
        This module provides a wizard to generate the GSTR-3B Return in Excel format.
        It generates a summarized view of Outward Supplies, Interstate B2C Supplies (3.2), Eligible ITC (4), and Exempt Inward Supplies (5).
    """,
    'author': 'Antigravity',
    'depends': ['account', 'l10n_in', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/gstr3b_report_wizard_views.xml',
        'report/report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
