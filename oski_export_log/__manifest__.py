{
    "name": "Export Log",
    "version": "20.0.1.0.1",
    "category": "Technical",
    "summary": "Know who takes which data out of your database: model, fields, number of rows, date.",
    "description": """
Odoo offers only an on/off switch: the export permission is granted, or it is
not. Once granted, nothing more is known — not which model was dumped, not how many rows went
out, not when.

This module logs every export actually performed: the author, the model, the list of requested
fields and the number of rows produced. It prevents nothing and slows nothing down; it makes
visible what goes out.

Exports refused for lack of rights produce no line: the log only records what
actually left the database.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_export_log.png",
    ],
    "data": [
        "security/ir.access.csv",
        "views/oski_export_log_views.xml",
    ],
    "installable": True,
    "application": False,
}
