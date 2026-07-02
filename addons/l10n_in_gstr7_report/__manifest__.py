{
    'name': 'GSTR-7 Report (GST TDS)',
    "version": "19.0.1.0.0",
    'category': 'Accounting/Localizations',
    'summary': 'Export GSTR-7 GST TDS Report to Excel',
    'description': """
        This module provides a wizard to generate the GSTR-7 Return (Tax Deducted at Source) in Excel format.
        Users can define exactly which TDS taxes should be checked. The engine then aggregates CGST, SGST, IGST deductions and base values.
    """,
    'author': 'Antigravity',
    'depends': ['account', 'l10n_in', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/gstr7_report_wizard_views.xml',
        'report/report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
