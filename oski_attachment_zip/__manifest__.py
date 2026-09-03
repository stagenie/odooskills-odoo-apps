{
    "name": "OdooSkills — Pièces jointes en archive",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Toutes les pièces jointes d'une fiche, ou de plusieurs, téléchargées en une archive ZIP.",
    "description": """
Odoo sait zipper les fichiers **d'un message** du fil de discussion. Personne
ne range ses documents ainsi : une commande porte le bon signé dans un
message, le plan dans un autre, et le reste dans la boîte à pièces jointes.
Les récupérer demande autant de clics que de fichiers.

Ce module ajoute au menu d'actions l'entrée **Télécharger les pièces jointes
(ZIP)** :

- depuis une fiche, tous ses fichiers ;
- depuis une liste, ceux de la sélection, rangés dans un dossier par fiche.

L'entrée s'active modèle par modèle, depuis **Paramètres → Technique →
Structure de la base de données → Téléchargement groupé (ZIP)**.

Les fichiers se lisent avec les droits de qui les demande : les pièces d'une
fiche illisible ne partent pas dans l'archive. Les valeurs de champs binaires
et les pièces servies par une URL en sont écartées — les premières ne sont pas
des pièces jointes, les secondes n'ont aucun contenu à archiver.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_menu.png",
        "static/description/screenshot_02_models.png",
    ],
    "data": [
        "views/ir_model_views.xml",
    ],
    "installable": True,
    "application": False,
}
