{
    'name': 'Custom Accounting Reports API',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Provides JSON API for accounting reports and connects with Chrome Extension',
    'author': 'Antigravity',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/report_views.xml',
        'views/report_menus.xml',
    ],
    'installable': True,
    'application': False,
}
