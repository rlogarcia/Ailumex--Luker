{
    'name': 'Fleet Checklist',
    'version': '1.0',
    'category': 'Fleet',
    'summary': 'Checklists diarios de vehículos',
    'depends': ['base', 'fleet_base_ext'],
    'data': [
        'security/ir.model.access.csv',
        'data/chk_sequences.xml',
        'views/chk_check_dia.xml',
        'views/chk_plantilla.xml',
        'views/chk_items.xml',
        'views/chk_categoria.xml',
        'views/chk_base_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fleet_checklist/static/src/css/chk_form.css',
        ],
    },
    'installable': True,
    'application': True,
}
