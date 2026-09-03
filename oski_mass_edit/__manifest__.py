{
    "name": "OdooSkills — Édition en masse",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Modifiez un champ sur toute une sélection depuis la vue liste, sans passer par chaque fiche.",
    "description": """
Sélectionnez des enregistrements dans n'importe quelle vue liste, ouvrez « Édition en masse »
depuis le menu Actions, choisissez le champ et la valeur : tous les enregistrements retenus sont
mis à jour d'un coup. Un administrateur déclare une fois les modèles concernés ; l'entrée de menu
apparaît alors dans leur vue liste. Les droits d'accès et les règles d'enregistrement d'Odoo
s'appliquent normalement — le module n'écrit jamais en sudo.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_menu_actions.png",
        "static/description/screenshot_02_assistant.png",
        "static/description/screenshot_03_modeles_ouverts.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/oski_mass_edit_wizard_views.xml",
        "views/oski_mass_edit_config_views.xml",
    ],
    "installable": True,
    "application": False,
}
