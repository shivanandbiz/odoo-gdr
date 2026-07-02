{
    'name': 'GDR Enterprise Balance Sheet',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Enterprise-style hierarchical Balance Sheet report for Odoo Community',
    'author': 'GDR Mektek',
    'depends': ['account', 'custom_accounting_reports'],
    'data': [
        'security/ir.model.access.csv',
        'views/actions.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gdr_balance_sheet/static/src/balance_sheet/balance_sheet.js',
            'gdr_balance_sheet/static/src/balance_sheet/balance_sheet.xml',
            'gdr_balance_sheet/static/src/balance_sheet/balance_sheet.css',
            'gdr_balance_sheet/static/src/profit_loss/profit_loss.js',
            'gdr_balance_sheet/static/src/profit_loss/profit_loss.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
