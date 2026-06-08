{
    "name": "OdooSkills — Demande de développement",
    "version": "19.0.1.0.0",
    "category": "Website",
    "summary": "Formulaire de demande de développement de module sur-mesure",
    "description": "Permet aux utilisateurs connectés de soumettre une demande de "
                   "développement d'un module Odoo, triée dans un pipeline backend. "
                   "Module publié sur le store (standard) ou exclusif (premium).",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
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
