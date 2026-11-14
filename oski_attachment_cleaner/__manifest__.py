{
    "name": "Attachment Cleaner",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Find orphan attachments and redundant copies, measure their size, and purge them under control.",
    "description": """
A database's filestore ages badly: a deleted record leaves its attachments
behind, and the same file ends up attached two or three times to the same
document. Odoo offers no inventory, and its automatic cleanup only touches
what it produced itself.

This module lists, measures, then purges on request:

- **orphans** — the attachment points to a record that no longer exists;
- **redundant copies** — same checksum, same document, several times.

Nothing is deleted without a prior report, and every purge leaves a named
trail.

Excluded by design, and never offered: binary field values, files served by
a URL, public attachments, those of views, and anything more recent than the
selected minimum age.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_scan.png",
        "static/description/screenshot_02_purges.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_attachment_purge_views.xml",
        "wizards/oski_attachment_cleaner_views.xml",
    ],
    "installable": True,
    "application": False,
}
