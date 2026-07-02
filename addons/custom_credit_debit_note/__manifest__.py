{
    'name': 'Custom Credit and Debit Note',
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Add item selection and GST reason code to credit and debit notes',
    'description': """
        This module adds custom functionality to the standard Odoo Credit Note and Debit Note wizards:
        - GST Reason Code dropdown.
        - Item Selection tab to select specific lines and adjust quantities to reverse/debit.
    """,
    'author': 'Antigravity',
    'depends': ['account', 'account_debit_note', 'l10n_in'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'wizard/account_move_reversal_views.xml',
        'wizard/account_debit_note_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
