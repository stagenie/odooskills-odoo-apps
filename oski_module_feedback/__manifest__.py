{
    "name": "Module Change Requests",
    "version": "19.0.1.0.0",
    "category": "Website",
    "summary": "Let store customers request changes, improvements or report bugs on a paid module.",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["oski_app_store", "website", "portal", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "security/oski_module_feedback_rules.xml",
        "data/ir_sequence_data.xml",
        "data/mail_template_data.xml",
        "views/oski_module_feedback_views.xml",
        "views/oski_module_views.xml",
        "templates/feedback_form_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "oski_module_feedback/static/src/scss/feedback.scss",
            "oski_module_feedback/static/src/js/feedback_form.js",
        ],
    },
    "installable": True,
    "application": False,
}
