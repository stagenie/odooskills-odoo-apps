{
    "name": "Login Log",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "summary": "Every login and every failure, with its username, IP address and date.",
    "description": """
Odoo keeps the date of the last login and nothing else: neither failed attempts nor the
addresses people log in from. Failures go to the server log file, which nobody
opens — and which disappears on rotation.

This module keeps a log you can view from the interface: username entered, recognized
user if any, success or failure, IP address, date. A burst of failures on the same
username then stands out at a glance.

Failures are written in a transaction of their own: a refused attempt rolls back everything else,
and a record written in the login's transaction would disappear along with it.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_login_log.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_login_log_views.xml",
    ],
    "installable": True,
    "application": False,
}
