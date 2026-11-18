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
    ],
    "installable": True,
    "application": False,
}
