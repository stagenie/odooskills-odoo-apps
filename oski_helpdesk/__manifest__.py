{
    "name": "Assistance (Helpdesk) — Oski",
    "version": "19.0.1.0.0",
    "category": "Services/Helpdesk",
    "summary": "Tickets d'assistance : équipes, étapes, alias email, assignation",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/helpdesk_security.xml",
        "security/ir.model.access.csv",
        "views/helpdesk_tag_views.xml",
    ],
    "installable": True,
    "application": True,
}
