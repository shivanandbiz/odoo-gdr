{
    'name': 'GDR Enterprise Reports',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Adds missing Enterprise-style accounting reports: Cash Flow Statement, Executive Summary, Depreciation Schedule, Deferred Revenue/Expense, Loans Analysis',
    'author': 'GDR Mektek',
    'depends': ['account', 'custom_accounting_reports'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/report_wizard_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
