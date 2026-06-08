{
    "name": "OdooSkills — Personnalisation Login",
    "version": "17.0.1.0.0",
    "category": "Technical",
    "summary": "Personnalise la page de connexion (fond, couleur, logo)",
    "description": """
Personnalise la page de connexion Odoo depuis les Réglages : couleur de
fond, couleur d'accent (boutons, liens) et logo. Aucun code requis.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["web", "base_setup"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/res_company_views.xml",
        "views/login_templates.xml",
    ],
    "installable": True,
    "application": False,
}
