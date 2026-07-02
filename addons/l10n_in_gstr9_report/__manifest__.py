# -*- coding: utf-8 -*-
{
    'name': 'GSTR-9 Annual Return Excel Report',
    "version": "19.0.1.0.0",
    'category': 'Accounting/Localizations',
    'summary': 'Generate GSTR-9 Annual Return Report',
    'description': """
        This module provides the capability to generate the GSTR-9 Annual Return report in Excel format.
        It groups Inward and Outward supplies based on the Indian Localization (l10n_in).
    """,
    'author': 'Custom',
    'depends': ['account', 'l10n_in', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/gstr9_report_wizard_views.xml',
        'report/report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
