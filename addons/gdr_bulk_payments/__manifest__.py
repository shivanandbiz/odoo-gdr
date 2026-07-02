{
    'name': 'GDR Bulk Payments',
    'version': '1.0.0',
    'category': 'Accounting',
    'summary': 'Manage Bulk Payments, Vendor Advances, and History in Accounting',
    'description': """
        This module provides:
        - Bulk Payment management for vendors.
        - Vendor Advances shortcut.
        - History Bulk Payments tracking.
    """,
    'author': 'Antigravity',
    'depends': ['account', 'payment'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'wizard/bulk_payment_wizard_views.xml',
        'views/bulk_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
