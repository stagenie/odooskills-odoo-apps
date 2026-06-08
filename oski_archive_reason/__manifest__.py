{
    "name": "OdooSkills — Motif d'archivage",
    "version": "16.0.1.0.0",
    "category": "Productivity",
    "summary": "Demande un motif obligatoire avant d'archiver un contact",
    "description": """
Lorsqu'un utilisateur archive un contact, une fenêtre demande un motif
obligatoire. Le motif est enregistré dans le fil de discussion (chatter)
du contact, pour garder une trace de la raison de l'archivage.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["mail", "contacts"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/archive_reason_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
