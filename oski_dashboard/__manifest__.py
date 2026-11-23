{
    'name': "OSKI Dashboard",
    'version': '20.0.1.0.2',
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
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_dashboard.png",
        "static/description/screenshot_02_edit_mode.png",
        "static/description/screenshot_03_widget_editor.png",
    ],
    'depends': ['web', 'web_tour'],
    'data': [
        'security/dashboard_security.xml',
        'security/ir.access.csv',
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
