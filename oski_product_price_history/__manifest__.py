{
    "name": "OdooSkills — Historique des prix",
    "version": "19.0.1.0.0",
    "category": "Sales/Sales",
    "summary": "Chaque changement de prix de vente ou de coût, avec l'écart, la date et l'auteur.",
    "description": """
Odoo n'a plus d'historique de prix. Le prix affiché est le prix d'aujourd'hui ;
celui d'avant la dernière hausse n'existe plus nulle part, et personne ne peut
dire qui l'a changé ni quand.

Ce module inscrit chaque mouvement :

- le **prix de vente** de l'article ;
- le **coût**, par variante et par société — c'est un champ dépendant de la
  société, deux filiales peuvent valoriser le même article différemment ;
- l'ancienne valeur, la nouvelle, l'écart en monnaie et en pourcentage, la
  date et l'auteur.

La liste se filtre sur les hausses, les baisses, l'année en cours ; la courbe
montre la trajectoire d'un article. Un bouton sur la fiche article ouvre son
seul historique.

**Aucune purge automatique**, contrairement aux journaux techniques de la
gamme : un historique de prix qui s'efface au bout de trente jours ne répond
plus à la seule question qu'on lui pose.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["product"],
    "images": [
        "static/description/screenshot_01_history.png",
        "static/description/screenshot_02_product.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_product_price_history_views.xml",
    ],
    "installable": True,
    "application": False,
}
