# -*- coding: utf-8 -*-
{
    "name": "Low Stock Alert",
    "version": "19.0.1.0.1",
    "category": "Inventory/Inventory",
    "summary": "Avoid silent stockouts: an alert threshold per product, red rows and a daily activity for the inventory manager.",
    "description": """
Set an alert threshold per product. As soon as the available quantity
drops below that threshold, the product is flagged as "low stock":
red rows in the list, a dedicated filter, and a daily activity created
automatically for the inventory manager. Built-in duplicate prevention. No
technical setup required.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_threshold.png",
        "static/description/screenshot_02_low_filter.png",
        "static/description/screenshot_03_activity.png",
    ],
    "depends": ["stock", "mail"],
    "data": [
        "data/ir_cron.xml",
        "views/product_views.xml",
    ],
    "installable": True,
    "application": False,
}
