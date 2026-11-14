{
    "name": "Price History",
    "version": "20.0.1.0.0",
    "category": "Sales/Sales",
    "summary": "Every change to a sales price or a cost, with the difference, the date and the author.",
    "description": """
Odoo no longer has a price history. The price shown is today's price;
the one before the last increase no longer exists anywhere, and nobody can
say who changed it or when.

This module records every change:

- the product's **sales price**;
- the **cost**, per variant and per company — it is a company-dependent
  field, so two subsidiaries can value the same product differently;
- the old value, the new one, the difference in currency and as a percentage,
  the date and the author.

The list can be filtered on increases, decreases and the current year; the chart
shows a product's trend. A button on the product form opens that product's
history alone.

**No automatic purge**, unlike the technical logs in the
range: a price history that wipes itself after thirty days can no longer
answer the only question anyone asks it.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["product"],
    "images": [
        "static/description/screenshot_01_history.png",
        "static/description/screenshot_02_product.png",
    ],
    "data": [
        "security/ir.access.csv",
        "views/oski_product_price_history_views.xml",
    ],
    "installable": True,
    "application": False,
}
