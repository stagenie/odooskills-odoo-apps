{
    "name": "OdooSkills — Garde-fou de suppression",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Interdisez la suppression modèle par modèle, réservez-la à quelques groupes, et gardez la trace de chaque effacement.",
    "description": """
Une suppression ne laisse aucune trace dans Odoo : l'enregistrement disparaît, et avec lui son
chatter. Ce module ferme la porte modèle par modèle — commandes, contacts, factures, ce que vous
décidez — et n'ouvre l'exception qu'aux groupes que vous désignez. Chaque suppression réellement
exécutée sur un modèle surveillé est inscrite dans un journal consultable : qui, quoi, quand.

Les opérations système (installation, mise à jour, désinstallation, tâches planifiées) ne sont
jamais bloquées : le garde-fou protège l'interface, pas la maintenance.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_regles.png",
        "static/description/screenshot_02_refus.png",
        "static/description/screenshot_03_journal.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_delete_rule_views.xml",
        "views/oski_delete_log_views.xml",
    ],
    "installable": True,
    "application": False,
}
