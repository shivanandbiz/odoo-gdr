{
    'name': 'Custom E-Waybill Automation',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Automatically populate transporter details based on Transporter Doc No',
    'description': """
        This module adds automation to the e-Waybill form:
        1. When Transporter Doc No is entered and matches a partner's GSTIN, the Transporter field is automatically filled.
        2. When a Transporter is selected, the Transporter Doc No is automatically filled with their GSTIN.
    """,
    'author': 'Antigravity',
    'depends': ['l10n_in_ewaybill'],
    'data': [
        'views/l10n_in_ewaybill_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
