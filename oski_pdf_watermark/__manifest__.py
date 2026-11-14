{
    "name": "Report Watermark",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "summary": "DRAFT, COPY, CANCELLED: a conditional watermark on any QWeb report.",
    "description": """
An unconfirmed quotation, a cancelled invoice and a reprint come out of the
printer looking exactly like the valid document. Odoo offers no
watermark.

This module adds one, decided by a rule:

- a **report** — any of them, from the quotation to the delivery slip;
- a **condition** on the document, written as a domain and checked on
  save, never code executed at print time;
- a **word**, its color, its opacity, its angle, its size.

The watermark is drawn in the body of the report and repeats on **every
page**, including those of a long document.

When a print job groups documents that call for different watermarks, none
is applied: a fixed element applies to every page of the generated file, and
would wrongly mark the other documents.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["web"],
    "images": [
        "static/description/screenshot_01_report.png",
        "static/description/screenshot_02_rules.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/report_watermark_templates.xml",
        "views/oski_report_watermark_views.xml",
    ],
    "installable": True,
    "application": False,
}
