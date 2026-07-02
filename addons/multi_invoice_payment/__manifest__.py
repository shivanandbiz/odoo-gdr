{
    'name': 'Multi Invoice Payment',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Bulk Payment for Customer Invoices',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/multi_invoice_payment_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
