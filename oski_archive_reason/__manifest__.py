{
    "name": "Archive Reason",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "summary": "Keep a record of every archiving: a mandatory reason entered before the action, kept in the contact's chatter.",
    "description": """
No more archiving without an explanation. When a user tries to archive
a contact, a dialog opens and requires a reason (mandatory field).
The reason is then posted automatically in the contact's
chatter, for a complete and auditable history.

Key features:
- Archiving blocked without justification (mandatory field)
- Reason recorded in the contact's chatter
- Zero configuration after installation
- Compatible with multi-selection from the list view
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["mail", "contacts"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/archive_reason_wizard_views.xml",
    ],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_reason_wizard.png",
        "static/description/screenshot_02_reason_in_chatter.png",
    ],
    "installable": True,
    "application": False,
}
