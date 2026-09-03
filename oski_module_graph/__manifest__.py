{
    "name": "OdooSkills — Graphe des dépendances",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Voyez d'un coup d'œil ce qui dépend de quoi dans votre base, en SVG.",
    "description": """
La liste des applications dit ce qui est installé. Elle ne dit pas ce qui tient
quoi : quel module s'effondrerait si on désinstallait celui-ci, ni combien de
couches séparent une personnalisation du cœur.

Ce module dessine le graphe des dépendances des modules installés : un étage
par profondeur, une flèche par dépendance, le tout en SVG lisible et
imprimable. Depuis la fiche d'un module, un bouton montre son propre arbre.

Aucune bibliothèque tierce, aucun appel réseau : le dessin est produit par le
serveur.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_graph.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/oski_module_graph_views.xml",
        "views/ir_module_module_views.xml",
    ],
    "installable": True,
    "application": False,
}
