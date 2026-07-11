{
    'name': 'OSKI Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Productivity',
    'summary': "Constructeur de tableaux de bord drag-and-drop",
    'description': """Composez vos tableaux de bord Odoo sans code : grille drag-and-drop,
9 types de widgets (KPI, barres, lignes, aires, camembert, donut, liste, jauge, texte),
périodes calendaires avec comparaison N-1, favoris et auto-refresh.
Chaque widget lit ses données avec les droits de l'utilisateur connecté
(règles propriétaire / partage en lecture par groupes).""",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'support': 'support@odooskills.com',
    'license': 'LGPL-3',
    'images': ['static/description/screenshot_01_tableau_de_bord.png'],
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
