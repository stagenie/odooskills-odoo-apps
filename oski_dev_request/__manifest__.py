{
    "name": "OdooSkills — Demande de développement",
    "version": "19.0.1.0.0",
    "category": "Website",
    "summary": "Centralisez les demandes de modules sur-mesure dans un pipeline structuré — plus aucun email de specs perdu.",
    "description": """
Vos clients veulent des modules spécifiques mais les échanges par email s'éparpillent.
Ce module ajoute un formulaire public /apps/demande-developpement et un pipeline Kanban
backend pour suivre chaque demande (Nouveau → En analyse → Devis → Accepté → Livré).
Budget, version Odoo cible et pièces jointes capturés dès la soumission.
Accusé de réception automatique. Lien vers le module livré à la clôture.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["oski_app_store", "website", "mail", "portal"],
    "data": [
        "security/ir.model.access.csv",
        "security/oski_dev_request_rules.xml",
        "data/ir_sequence_data.xml",
        "data/mail_template_data.xml",
        "views/oski_dev_request_views.xml",
        "templates/dev_request_templates.xml",
    ],
    "installable": True,
    "application": False,
}
