{
    'name': 'OSKI Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Productivity',
    'summary': "Constructeur de tableaux de bord drag-and-drop",
    'description': "Tableaux de bord personnalisables : KPI, graphiques, listes, jauges. Données lues avec les droits de l'utilisateur.",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'license': 'LGPL-3',
    'depends': ['web', 'web_tour'],
    'data': [
        'security/dashboard_security.xml',
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'oski_dashboard/static/src/**/*',
        ],
        'web.assets_tests': [
            'oski_dashboard/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'oski_dashboard/static/tests/**/*',
            ('remove', 'oski_dashboard/static/tests/tours/**/*'),
        ],
    },
    'installable': True,
    'application': True,
}
