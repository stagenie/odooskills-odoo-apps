# -*- coding: utf-8 -*-
{
    "name": "Pistes dormantes CRM",
    "version": "16.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Détecte les pistes et opportunités sans mouvement depuis X jours",
    "description": """
Pistes dormantes CRM
====================

Met en évidence les pistes et opportunités qui n'ont connu aucun mouvement
depuis un nombre de jours configurable. Idéal pour relancer les affaires
oubliées dans le pipeline.

Le seuil d'inactivité se règle dans les Réglages du CRM. Une colonne
« Jours d'inactivité » et un surlignage des lignes apparaissent dans le
pipeline, et un filtre « Dormantes » permet d'isoler les affaires à relancer.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["crm"],
    "data": [
        "views/crm_lead_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": False,
}
