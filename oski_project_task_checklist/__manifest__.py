# -*- coding: utf-8 -*-
{
    "name": "Checklist d'étapes sur les tâches de projet",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "summary": "Ne laissez plus rien passer : chaque tâche gagne une checklist cochable avec barre de progression et assignation par étape.",
    "description": """
Checklist d'étapes sur les tâches de projet
===========================================

Les micro-étapes d'une tâche finissent souvent dans les commentaires ou les
e-mails — sources d'oublis. Ce module ajoute un onglet « Checklist » sur chaque
tâche de projet pour lister, cocher et assigner chaque sous-étape.

- Onglet « Checklist » avec liste éditable inline (réordonnable par glisser-déposer).
- Barre de progression calculée automatiquement (% d'étapes terminées).
- Assignation de chaque étape à un utilisateur différent.
- Colonne d'avancement optionnelle dans la vue liste des tâches.

Aucune configuration requise : fonctionne dès l'installation.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "images": ["static/description/screenshot_01_onglet_checklist.png"],
    "depends": ["project"],
    "data": [
        "security/ir.model.access.csv",
        "views/project_task_views.xml",
    ],
    "installable": True,
    "application": False,
}
