{
    "name": "OdooSkills — Personnalisation Login",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Affichez votre marque dès la connexion : couleur de fond, couleur d'accent et logo personnalisés sans code.",
    "description": """
La page de connexion Odoo affiche par défaut les couleurs du framework.
Ce module permet à tout administrateur de choisir une couleur de fond,
une couleur d'accent (boutons, liens) et un logo propre à chaque société
— directement depuis les Réglages, sans modifier le code source.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
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
