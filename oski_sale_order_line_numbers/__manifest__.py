# -*- coding: utf-8 -*-
{
    "name": "Sales Line Numbers",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "Number every product line of your quotations and orders — on screen and on the PDF — for unambiguous customer exchanges.",
    "description": """
Automatic numbering of quotation and sales order lines
======================================================

This module adds an "N°" column that automatically numbers (1, 2, 3, …)
the product lines of every quotation and sales order, on screen as well as
on the printed PDF.

- Section, subsection and note lines are not numbered.
- Numbering follows the display order of the lines and updates
  automatically when the lines are reordered.
- The "N°" column appears in first position in the lines table and at the
  start of the PDF report.

No configuration is needed: the module works as soon as it is
installed.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_order_lines.png",
        "static/description/screenshot_02_pdf.png",
    ],
    "depends": ["sale_management"],
    "data": [
        "views/sale_order_views.xml",
        "report/sale_report_templates.xml",
    ],
    "installable": True,
    "application": False,
}
