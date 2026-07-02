# -*- coding: utf-8 -*-
{
    'name': 'GDR Mektek Website Theme',
    'version': '1.0',
    'category': 'Theme/Industrial',
    'summary': 'Professional Corporate Website for GDR Mektek Pvt Ltd',
    'description': """
        Custom website theme and homepage for GDR Mektek Pvt Ltd.
        Specializing in Material Handling, SPMs, and Testing Solutions.
    """,
    'author': 'Antigravity',
    'depends': ['website'],
    'data': [
        'views/homepage.xml',
        'views/snippets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'gdr_website_theme/static/src/scss/theme.scss',
        ],
    },
    'installable': True,
    'application': False,
}
