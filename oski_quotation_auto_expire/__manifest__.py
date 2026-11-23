{
    "name": "Quotation Auto-Expiry",
    "version": "20.0.1.0.1",
    "category": "Sales",
    "summary": "Expired quotations cancel themselves, and the salesperson gets a reminder before the deadline.",
    "description": """
Odoo computes an expiration date on every quotation, can tell you it has
expired... and does nothing about it. Dead quotations pile up in the funnel,
skew the forecasts and the pipeline amount, and nobody ever reopens them.

This module closes the loop:

- a **reminder** to the salesperson, as an activity, a few days before
  the deadline: the delay is adjustable, and never one more email;
- automatic **expiry** of quotations whose expiration date has passed,
  with a note in the record stating why and when.

Both settings are independent and live on the company: a subsidiary that
sells by the week and a parent company that sells by the quarter do not run
at the same pace.

The reminder runs **before** the expiry in the same night: a quotation
followed up in the morning and canceled in the evening would make the
salesperson look like a liar.

Locked quotations are never touched.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["sale"],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_expired.png",
        "static/description/screenshot_02_settings.png",
        "static/description/screenshot_03_expired_filter.png",
    ],
    "data": [
        "data/ir_cron.xml",
        "views/sale_order_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
