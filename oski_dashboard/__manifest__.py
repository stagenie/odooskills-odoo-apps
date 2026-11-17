{
    'name': "OSKI Dashboard",
    'version': '18.0.1.0.1',
    'category': 'Productivity',
    'summary': "Drag-and-drop dashboard builder",
    'description': """Build your Odoo dashboards without code: drag-and-drop grid,
9 widget types (KPI, bars, lines, areas, pie, donut, list, gauge, text),
calendar periods with previous-period comparison, favorites and auto-refresh.
Each widget reads its data with the logged-in user's access rights
(owner / read-sharing by group rules).""",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'support': 'apps@odooskills.com',
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
