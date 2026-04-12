{
    'name': 'Fleet Base Ext',
    'version': '1.0',
    'category': 'Fleet',
    'summary': 'Extensión de flota: vehículos, conductores, sedes, asignaciones',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/flo_vehiculo_views.xml',
        'views/flo_sede_operativa_views.xml',
        'views/flo_centro_costo_views.xml',
        'views/rrhh_empleado_views.xml',
        'views/flo_vehiculo_conductor_views.xml',
        'views/seg_views.xml',
        'views/fleet_base_ext_menus.xml',
        'views/assets.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fleet_base_ext/static/src/css/kanban_vehiculo.css',
            'fleet_base_ext/static/src/css/kanban_conductor.css',        ],
    },
    'installable': True,
    'application': True,
}