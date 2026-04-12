{
    'name': 'Fleet Issue Control',
    'version': '1.0',
    'category': 'Fleet',
    'summary': 'fleet_issue_control',
    'depends': ['base', 'fleet_base_ext', 'fleet_checklist'],
    'data': [
        'security/ir.model.access.csv',
        'views/chk_novedades.xml',
        'views/blo_bloqueos.xml',
        'views/fleet_issue_control_menus.xml',
        'data/sequences.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fleet_issue_control/static/src/css/kanban_novedades.css',
        ],
    },
    'installable': True,
    'application': False,
}