{
    'name': 'Code-barres Stock',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Stock',
    'summary': "Interface tactile de scan code-barres pour les opérations de stock : "
               "réception, expédition, inventaire, transfert, consultation",
    'description': """Application tactile mobile-first de lecture code-barres pour Odoo 19 CE.
Cinq écrans dédiés — réception, expédition, inventaire interne, transfert et
consultation — avec saisie au scan ou manuelle, retour sonore et vibration,
gestion des reliquats, étiquettes d'emplacement et code-barres sur bon de livraison.
Journal de session « Ma session » retraçant chaque scan de l'opérateur.
Fonctionne avec n'importe quelle douchette clavier (USB/Bluetooth) ou la caméra.""",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'support': 'apps@odooskills.com',
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
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
    },
    'installable': True,
    'application': True,
}
