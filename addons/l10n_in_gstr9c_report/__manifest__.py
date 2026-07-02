{
    'name': 'GSTR-9C Reconciliation Statement Excel Report',
    "version": "19.0.1.0.0",
    'category': 'Accounting/Localizations',
    'summary': 'Export GSTR-9C Reconciliation Statement to Excel',
    'description': """
        This module provides a wizard to generate the GSTR-9C Reconciliation Statement in Excel format.
        It extracts data from posted journal items and groups them according to GSTR-9C requirements (Turnover, Tax, ITC reconciliation).
    """,
    'author': 'Antigravity',
    'depends': ['account', 'l10n_in', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/gstr9c_report_wizard_views.xml',
        'report/report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
