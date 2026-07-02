{
    'name': 'Indian GST Reports (Custom)',
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'summary': 'GSTR-1 and GSTR-3B Reports for Indian Localization',
    'description': """
        This module provides GSTR-1 and GSTR-3B reports for Odoo Community.
        It uses the GSTR section classification on move lines.
    """,
    'author': 'Antigravity',
    'depends': ['l10n_in', 'account', 'l10n_in_ewaybill'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_report_gstr3b_data.xml',
        'views/gst_report_menu.xml',
        'views/report_gstr1.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
