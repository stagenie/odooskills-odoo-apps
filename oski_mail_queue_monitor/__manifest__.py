{
    "name": "Email Queue Monitor",
    "version": "19.0.1.0.1",
    "category": "Technical",
    "summary": "Find out the same day that your emails have stopped going out, not three months later.",
    "description": """
A misconfigured outgoing server makes no noise: emails pile up in
``mail.mail``, the queue grows, and nobody finds out until a customer asks
why they received nothing. Odoo can resend a failed email, but monitors
nothing.

This module checks the queue every day: how many are waiting, how many have
failed, how long the oldest email has been waiting, and for what reasons. The
verdict is recorded, and an activity is assigned to the administrators when
the queue degrades.

The alert does not go through email — that would be asking the patient to
deliver their own diagnosis.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["mail"],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_checks.png",
        "static/description/screenshot_02_check.png",
        "static/description/screenshot_03_failed.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/oski_mail_queue_check_views.xml",
    ],
    "installable": True,
    "application": False,
}
