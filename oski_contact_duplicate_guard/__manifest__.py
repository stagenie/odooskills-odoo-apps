{
    "name": "OdooSkills — Anti-doublon Contacts",
    "version": "19.0.1.0.0",
    "category": "Contacts",
    "summary": "Évitez les doublons clients : alerte dès qu'un email ou téléphone existe déjà.",
    "description": """
Avertit l'utilisateur dès la saisie lorsqu'un contact partage le même email
ou le même téléphone qu'un contact existant. La détection est non bloquante :
le contact peut être créé, mais un bandeau et un lien vers le doublon possible
sont affichés. Email et téléphone activables séparément depuis les Réglages.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["contacts", "base_setup"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
    ],
    "images": [
        "static/description/screenshot_01_bandeau_doublon.png",
        "static/description/screenshot_02_alerte_email_doublon.png",
        "static/description/screenshot_03_liste_doublons.png",
    ],
    "installable": True,
    "application": False,
}
