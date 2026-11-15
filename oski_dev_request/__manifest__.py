{
    "name": "OdooSkills — Development Request",
    "version": "19.0.4.0.2",
    "category": "Website",
    "summary": "Gather custom module requests in a structured pipeline — no more specs lost in emails.",
    "description": """
Your customers want specific modules, but email exchanges get scattered.
This module adds a public form /apps/demande-developpement and a backend Kanban
pipeline to follow each request (New → Under review → Quote sent → Accepted → Delivered).
Budget, target Odoo version and attachments are captured at submission.
Automatic acknowledgement. Link to the delivered module at closing.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["oski_app_store", "website", "mail", "portal"],
    "data": [
        "security/ir.model.access.csv",
        "security/oski_dev_request_rules.xml",
        "data/ir_sequence_data.xml",
        "data/mail_template_data.xml",
        "data/website_menu_data.xml",
        "views/oski_dev_request_views.xml",
        "templates/dev_request_templates.xml",
    ],
    "images": ["static/description/screenshot_01_pipeline_kanban.png"],
    "installable": True,
    "application": False,
}
