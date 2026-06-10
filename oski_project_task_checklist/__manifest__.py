# -*- coding: utf-8 -*-
{
    "name": "Checklist d'étapes sur les tâches de projet",
    "version": "16.0.1.0.0",
    "category": "Services/Project",
    "summary": "Ajoute une checklist d'étapes avec barre de progression aux tâches de projet",
    "description": """
Checklist d'étapes sur les tâches de projet
===========================================

Ce module ajoute à chaque tâche de projet un onglet « Checklist » permettant de
lister les étapes à réaliser, d'en cocher l'avancement et d'assigner chaque
étape à un utilisateur.

- Onglet « Checklist » avec liste éditable inline (réordonnable).
- Barre de progression indiquant le pourcentage d'étapes terminées.
- Colonne d'avancement dans la liste des tâches.

Aucune configuration n'est nécessaire : le module fonctionne dès son
installation.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["project"],
    "data": [
        "security/ir.model.access.csv",
        "views/project_task_views.xml",
    ],
    "installable": True,
    "application": False,
}
