{
    'name': 'Documents — GED',
    'version': '19.0.1.0.0',
    'category': 'Productivity/Documents',
    'summary': "Gestion électronique de documents : espaces, versionning, "
               "rattachement métier, droits par espace",
    'description': "GED Odoo 19 : organisez en espaces cloisonnés vos pièces "
                   "jointes et fichiers, avec versionning, aperçu, rattachement "
                   "aux enregistrements métier et droits par espace.",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'support': 'apps@odooskills.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/dms_security.xml',
        'security/ir.model.access.csv',
        'views/dms_workspace_views.xml',
        'views/dms_tag_views.xml',
        'views/dms_document_views.xml',
        'views/dms_file_wizard_views.xml',
        'views/dms_version_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/dms_menus.xml',
        'data/dms_data.xml',
    ],
    'demo': [
        'demo/dms_demo.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
}
