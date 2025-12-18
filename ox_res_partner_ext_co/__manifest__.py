# -*- coding: utf-8 -*-
{
    'name': "Terceros Colombia - Odoo Xpert SAS",

    'summary': """
        Información complementaria de terceros""",

    'description': """
        Información complementaria de terceros
    """,

    'author': "Odoo Xpert SAS",
    'website': "https://www.odooxp.com",

    'category': 'Services',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'contacts', 'l10n_latam_base', 'account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/res_partner_ext_co.xml',
        'views/res_partner_economic_activity.xml',
        'views/res_partner_society.xml',
        'views/res_city.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ox_res_partner_ext_co/static/src/css/odooxpert.css',
        ],
    },
}