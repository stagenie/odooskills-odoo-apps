{
    "name": "OdooSkills — Nettoyage des pièces jointes",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Repérez les pièces jointes orphelines et les copies redondantes, mesurez le poids, purgez sous contrôle.",
    "description": """
Le magasin de fichiers d'une base vieillit mal : un enregistrement supprimé
laisse ses pièces jointes derrière lui, et la même pièce finit attachée deux ou
trois fois au même document. Odoo ne propose aucun inventaire, et sa purge
automatique ne touche qu'à ce qu'il a lui-même produit.

Ce module recense, mesure, puis purge sur demande :

- les **orphelines** — la pièce désigne un enregistrement qui n'existe plus ;
- les **copies redondantes** — même empreinte, même document, plusieurs fois.

Rien n'est supprimé sans un relevé préalable, et chaque purge laisse une trace
nominative.

Sont écartées d'office, et jamais proposées : les valeurs de champs binaires,
les fichiers servis par une URL, les pièces publiques, celles des vues, et
tout ce qui est plus récent que l'âge minimum retenu.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_scan.png",
        "static/description/screenshot_02_purges.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_attachment_purge_views.xml",
        "wizards/oski_attachment_cleaner_views.xml",
    ],
    "installable": True,
    "application": False,
}
