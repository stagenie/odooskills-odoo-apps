{
    "name": "Attachments as ZIP",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "All the attachments of one record, or of several, downloaded as a single ZIP archive.",
    "description": """
Odoo can zip the files **of one message** in the chatter. Nobody files their
documents that way: an order carries the signed delivery slip in one
message, the drawing in another, and the rest in the attachment box.
Retrieving them takes as many clicks as there are files.

This module adds the **Download attachments (ZIP)** entry to the Actions
menu:

- from a record, all of its files;
- from a list, those of the selection, filed in one folder per record.

The entry is enabled model by model, from **Settings → Technical →
Database Structure → Bulk download (ZIP)**.

Files are read with the rights of whoever requests them: attachments of a
record they cannot read stay out of the archive. Binary field values and
attachments served by a URL are left out — the former are not attachments,
the latter have no content to archive.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_menu.png",
        "static/description/screenshot_02_models.png",
    ],
    "data": [
        "views/ir_model_views.xml",
    ],
    "installable": True,
    "application": False,
}
