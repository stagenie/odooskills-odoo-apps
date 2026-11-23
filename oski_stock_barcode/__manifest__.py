{
    'name': "Stock Barcode",
    'version': '18.0.1.0.2',
    'category': 'Inventory/Stock',
    'summary': "Touch barcode scanning interface for stock operations: receipt, delivery, inventory count, transfer, lookup",
    'description': """Mobile-first touch barcode scanning app for Odoo 19 CE.
Five dedicated screens — receipt, delivery, internal inventory count, transfer and
lookup — with scan or manual entry, audio and vibration feedback,
backorder handling, location labels and barcode on the delivery slip.
"My session" log tracing every scan by the operator.
Works with any keyboard-wedge scanner (USB/Bluetooth) or the camera.""",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'support': 'apps@odooskills.com',
    'license': 'LGPL-3',
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_home.png",
        "static/description/screenshot_02_receipt.png",
        "static/description/screenshot_03_inventory.png",
        "static/description/screenshot_04_lookup.png",
    ],
    'depends': ['stock', 'barcodes'],
    'data': [
        'security/ir.model.access.csv',
        'security/barcode_security.xml',
        'views/barcode_views.xml',
        'views/stock_views_inherit.xml',
        'views/report_inherit.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'oski_stock_barcode/static/src/scss/barcode.scss',
            'oski_stock_barcode/static/src/xml/barcode_templates.xml',
            'oski_stock_barcode/static/src/js/barcode_rpc.js',
            'oski_stock_barcode/static/src/js/scan_feedback.js',
            'oski_stock_barcode/static/src/js/qty_stepper.js',
            'oski_stock_barcode/static/src/js/product_search.js',
            'oski_stock_barcode/static/src/js/scan_banner.js',
            'oski_stock_barcode/static/src/js/picking_list.js',
            'oski_stock_barcode/static/src/js/barcode_receipt.js',
            'oski_stock_barcode/static/src/js/barcode_delivery.js',
            'oski_stock_barcode/static/src/js/barcode_inventory.js',
            'oski_stock_barcode/static/src/js/barcode_transfer.js',
            'oski_stock_barcode/static/src/js/barcode_consult.js',
            'oski_stock_barcode/static/src/js/barcode_session.js',
            'oski_stock_barcode/static/src/js/barcode_main.js',
        ],
        'web.assets_tests': [
            'oski_stock_barcode/static/tests/tours/*.js',
        ],
    },
    'installable': True,
    'application': True,
}
