{
    'name': 'Custom Bank Reconciliation',
    'version': '1.1',
    'category': 'Accounting',
    'summary': 'Bank Reconciliation for Odoo Community',
    'description': 'Adds bank reconciliation dashboard, views, and CSV import to Odoo Community.',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_journal_dashboard_view.xml',
        'views/bank_reconciliation_views.xml',
        'views/bank_statement_import_views.xml',
        'views/account_move_line_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
