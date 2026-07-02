# -*- coding: utf-8 -*-
{
    'name': 'Customer Account Statement',
    "version": "19.0.1.0.0",
    'category': 'Accounting',
    'summary': 'Customer & Vendor Account Statement with Running Balance',
    'description': """
        Adds a Statement tab on the Customer/Vendor form showing all transactions
        (Invoices, Payments, Credit Notes, Debit Notes) with a running balance.
        Similar to Zoho Books account statement view.
    """,
    'author': 'GDR Mektek',
    'license': 'LGPL-3',
    'depends': ['account', 'contacts', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/statement_wizard_views.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
        'report/statement_report.xml',
        'report/statement_report_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
