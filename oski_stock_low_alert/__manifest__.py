# -*- coding: utf-8 -*-
{
    "name": "OdooSkills — Alerte de stock bas",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Évitez les ruptures silencieuses : seuil d'alerte par produit, lignes rouges et activité quotidienne pour le responsable inventaire",
    "description": """
Définissez un seuil d'alerte par produit. Dès que la quantité disponible
descend en dessous de ce seuil, le produit est signalé en « stock bas » :
lignes rouges dans la liste, filtre dédié, et une activité quotidienne créée
automatiquement pour le responsable de stock. Anti-doublon intégré. Aucun
paramétrage technique requis.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "images": ["static/description/screenshot_01_seuil_produit.png"],
    "depends": ["stock", "mail"],
    "data": [
        "data/ir_cron.xml",
        "views/product_views.xml",
    ],
    "installable": True,
    "application": False,
}
