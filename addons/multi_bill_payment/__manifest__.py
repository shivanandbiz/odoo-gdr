{
    'name': 'Multi Bill Payment',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Bulk Payment for Vendor Bills',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/multi_bill_payment_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
