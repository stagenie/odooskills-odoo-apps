{
    "name": "OdooSkills — Motif d'archivage",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "summary": "Gardez une trace de chaque archivage : motif obligatoire saisi avant l'action, conservé dans le chatter du contact.",
    "description": """
Plus aucun archivage sans explication. Lorsqu'un utilisateur tente d'archiver
un contact, une fenêtre s'ouvre et exige un motif (champ obligatoire).
La raison est ensuite postée automatiquement dans le fil de discussion du
contact, pour un historique complet et auditable.

Fonctionnalités clés :
- Archivage bloqué sans justification (champ obligatoire)
- Motif enregistré dans le chatter du contact
- Zéro configuration après installation
- Compatible avec la multi-sélection depuis la vue liste
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["mail", "contacts"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/archive_reason_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
