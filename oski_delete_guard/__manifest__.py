{
    "name": "Delete Guard",
    "version": "19.0.1.0.1",
    "category": "Technical",
    "summary": "Block deletion model by model, reserve it for a few groups, and keep a record of every deletion.",
    "description": """
A deletion leaves no trace in Odoo: the record disappears, and its
chatter with it. This module closes the door model by model — orders, contacts, invoices, whatever you
decide — and only opens the exception to the groups you designate. Every deletion actually
performed on a monitored model is written to a searchable log: who, what, when.

System operations (installation, upgrade, uninstallation, scheduled actions) are
never blocked: the guard protects the interface, not maintenance.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_rules.png",
        "static/description/screenshot_02_refusal.png",
        "static/description/screenshot_03_deletion_log.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_delete_rule_views.xml",
        "views/oski_delete_log_views.xml",
    ],
    "installable": True,
    "application": False,
}
