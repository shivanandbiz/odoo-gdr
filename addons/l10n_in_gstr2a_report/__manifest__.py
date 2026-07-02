{
    'name': 'GSTR-2A Reconciliation Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'GSTR-2A Reconciliation with inline summary and Excel download',
    'depends': ['account', 'l10n_in', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/gstr2a_report_wizard_views.xml',
        'report/report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
