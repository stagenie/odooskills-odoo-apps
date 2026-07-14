{
    'name': 'Atelier — Shop Floor',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'summary': "Exécution atelier tactile et responsive pour les ordres de travail — l'expérience Shop Floor en Community.",
    'description': """
Interface d'exécution atelier responsive (PC, tablette, mobile) pour piloter
les ordres de travail Odoo Community au doigt et au scan : sélection du poste,
démarrage/pause/fin d'un ordre, chrono, quantité produite et consommation des
composants. Aucune licence Enterprise requise.
""",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'support': 'support@odooskills.com',
    'license': 'LGPL-3',
    'depends': ['mrp', 'barcodes', 'web'],
    'data': [
        'views/shop_floor_action.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'oski_shop_floor/static/src/xml/shop_floor_templates.xml',
            'oski_shop_floor/static/src/js/shop_floor_app.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
}
