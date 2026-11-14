{
    "name": "Record Audit Log",
    "version": "20.0.1.0.0",
    "category": "Technical",
    "summary": "Who created, changed or deleted what, on the models you choose, without writing a line of code.",
    "description": """
Odoo's native tracking only covers fields marked "tracking" on models that
have a chatter. Everything else (a price changed on a product form, a bank
account rewritten, a deleted line) leaves no trace.

Choose the models to monitor, pick the operations (create, update, delete)
and, if you wish, the list of fields that matter. Every action is recorded
with its author, its date, and the "old value -> new value" detail.

System operations (installation, update, scheduled actions) are not logged:
the log keeps track of human actions, not of maintenance.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_journal.png",
        "static/description/screenshot_02_regles.png",
    ],
    "data": [
        "security/ir.access.csv",
        "views/oski_audit_rule_views.xml",
        "views/oski_audit_log_views.xml",
    ],
    "installable": True,
    "application": False,
}
