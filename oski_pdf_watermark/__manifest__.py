{
    "name": "OdooSkills — Filigrane sur les rapports",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "BROUILLON, COPIE, ANNULÉ : un filigrane conditionnel sur n'importe quel rapport QWeb.",
    "description": """
Un devis non confirmé, une facture annulée et une réimpression sortent de
l'imprimante avec exactement la même allure que le document valide. Odoo ne
propose aucun filigrane.

Ce module en pose un, décidé par une règle :

- un **rapport** — n'importe lequel, du devis au bon de livraison ;
- une **condition** sur le document, écrite en domaine et vérifiée à
  l'enregistrement, jamais du code exécuté au moment d'imprimer ;
- un **mot**, sa couleur, son opacité, son inclinaison, sa taille.

Le filigrane est dessiné dans le corps du rapport et se répète sur **toutes
les pages**, y compris celles d'un document long.

Quand une impression groupe des documents qui appellent des filigranes
différents, aucun n'est posé : un élément fixe vaut pour toutes les pages du
fichier produit, et marquerait les autres documents à tort.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["web"],
    "images": [
        "static/description/screenshot_01_report.png",
        "static/description/screenshot_02_rules.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/report_watermark_templates.xml",
        "views/oski_report_watermark_views.xml",
    ],
    "installable": True,
    "application": False,
}
