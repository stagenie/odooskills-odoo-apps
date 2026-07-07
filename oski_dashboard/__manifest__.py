{
    'name': 'OSKI Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Productivity',
    'summary': "Constructeur de tableaux de bord drag-and-drop",
    'description': "Tableaux de bord personnalisables : KPI, graphiques, listes, jauges. Données lues avec les droits de l'utilisateur.",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [
        'security/dashboard_security.xml',
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'oski_dashboard/static/src/**/*',
        ],
    },
    'installable': True,
    'application': True,
}
