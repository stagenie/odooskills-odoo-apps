{
    'name': 'Shop Floor',
    'version': '19.0.1.0.1',
    'category': 'Manufacturing',
    'summary': "Touch-friendly, responsive shop floor execution for work orders — the Shop Floor experience in Community.",
    'description': """
Responsive shop floor execution interface (PC, tablet, phone) to run
Odoo Community work orders by touch and by scan: work center selection,
start/pause/finish of an order, timer, produced quantity and component
consumption. No Enterprise license required.
""",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'support': 'apps@odooskills.com',
    'license': 'LGPL-3',
    'depends': ['mrp', 'barcodes', 'web'],
    'data': [
        'views/shop_floor_action.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'oski_shop_floor/static/src/scss/shop_floor.scss',
            'oski_shop_floor/static/src/xml/shop_floor_templates.xml',
            'oski_shop_floor/static/src/js/scan_feedback.js',
            'oski_shop_floor/static/src/js/use_shop_floor_scan.js',
            'oski_shop_floor/static/src/js/screen_workcenter.js',
            'oski_shop_floor/static/src/js/screen_orders.js',
            'oski_shop_floor/static/src/js/screen_detail.js',
            'oski_shop_floor/static/src/js/shop_floor_app.js',
        ],
        'web.assets_tests': [
            'oski_shop_floor/static/tests/tours/shop_floor_tour.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
}
