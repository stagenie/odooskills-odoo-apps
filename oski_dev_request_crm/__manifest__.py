{
    "name": "Demande de développement — Opportunités CRM",
    "version": "19.0.2.0.0",
    "category": "Website",
    "summary": "Chaque demande de module ouvre une opportunité dans le pipeline commercial.",
    "description": """
Une demande de développement est d'abord une affaire à gagner. Ce pont crée
l'opportunité CRM correspondante dès la soumission du formulaire public, avec
le contact, le besoin, la version d'Odoo visée et le budget annoncé — sans
retirer la demande de son propre pipeline technique.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["oski_dev_request", "crm"],
    "data": [
        "views/oski_dev_request_views.xml",
    ],
    "auto_install": True,
    "installable": True,
}
