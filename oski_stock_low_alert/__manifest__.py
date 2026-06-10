# -*- coding: utf-8 -*-
{
    "name": "OdooSkills — Alerte de stock bas",
    "version": "16.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Alerte simple et sans code lorsqu'un produit passe sous son seuil de stock",
    "description": """
Définissez un seuil d'alerte par produit. Dès que la quantité disponible
descend en dessous de ce seuil, le produit est signalé en « stock bas » :
lignes rouges dans la liste, filtre dédié, et une activité quotidienne créée
automatiquement pour le responsable de stock. Aucun paramétrage technique requis.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["stock", "mail"],
    "data": [
        "data/ir_cron.xml",
        "views/product_views.xml",
    ],
    "installable": True,
    "application": False,
}
