# -*- coding: utf-8 -*-
{
    "name": "Numérotation des lignes de devis/commande",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Numérote automatiquement les lignes produit des devis et commandes",
    "description": """
Numérotation automatique des lignes de devis et de commande
===========================================================

Ce module ajoute une colonne « N° » qui numérote automatiquement (1, 2, 3, …)
les lignes produit de chaque devis et bon de commande, à l'écran comme sur le
PDF imprimé.

- Les lignes de section, sous-section et note ne sont pas numérotées.
- La numérotation suit l'ordre d'affichage des lignes et se met à jour
  automatiquement lorsqu'on réordonne les lignes.
- La colonne « N° » apparaît en première position du tableau des lignes et en
  tête du rapport PDF.

Aucune configuration n'est nécessaire : le module fonctionne dès son
installation.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["sale_management"],
    "data": [
        "views/sale_order_views.xml",
        "report/sale_report_templates.xml",
    ],
    "installable": True,
    "application": False,
}
