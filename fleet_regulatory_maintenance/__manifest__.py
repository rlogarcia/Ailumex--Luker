{
    'name': 'Fleet Regulatory Maintenance',
    'version': '1.0',
    'category': 'Fleet',
    'summary': 'fleet_regulatory_maintenance',
    'depends': ['base', 'fleet_base_ext'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/mto_plan_mantenimiento.xml',
        'views/mto_eventos.xml',
        'views/mto_fichas.xml',
        'views/mto_regulatory_maintenance_menu.xml',
    ],
    'installable': True,
    'application': False,
}