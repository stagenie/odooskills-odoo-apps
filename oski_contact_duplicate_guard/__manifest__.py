{
    "name": "OdooSkills — Anti-doublon Contacts",
    "version": "19.0.1.0.0",
    "category": "Contacts",
    "summary": "Détecte les contacts en double (email / téléphone)",
    "description": """
Avertit l'utilisateur lorsqu'un contact saisi a le même email ou le même
téléphone qu'un contact existant. La détection est non bloquante : le contact
est créé, mais un lien vers le doublon possible est affiché. Activable par type
(email / téléphone) depuis les Réglages.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["contacts", "base_setup"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
