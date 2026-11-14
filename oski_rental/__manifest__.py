{
    'name': "Rental Management",
    'version': '19.0.1.0.0',
    'category': 'Services/Rental',
    'summary': "Rent out any type of resource: vehicles, rooms, machinery, equipment",
    'description': """
Generic rental management: individual resources, bookings, pickup/return with condition report, deposit, invoicing, late return alerts.
""",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'support': 'apps@odooskills.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'account', 'product'],
    'data': [
        'security/rental_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/product_data.xml',
        'data/ir_cron_data.xml',
        'views/rental_category_views.xml',
        'views/rental_asset_views.xml',
        'views/rental_unavailability_views.xml',
        'views/rental_order_views.xml',
        'views/rental_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/rental_menus.xml',
    ],
    'demo': [
        'demo/rental_demo.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
}
