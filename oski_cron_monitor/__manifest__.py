{
    "name": "Scheduled Action Monitor",
    "version": "20.0.1.0.0",
    "category": "Technical",
    "summary": "Every run of a scheduled action: duration, success, error, and the history that goes with it.",
    "description": """
Odoo keeps the date of a scheduled action's last run in ``lastcall`` and
shows it nowhere. The consecutive failure counter exists too, invisible. As
a result, an action that fails every night only shows up in the server log,
if someone thinks to open it.

This module records every run: start, duration, success or failure, and the
full error message. The action's "Runs" tab shows its history; the
"Scheduled Runs" menu shows them all, filterable on failures only.

Failures are written on a separate transaction: the action's transaction is
rolled back when it fails, and the failure is precisely what must be kept.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_runs.png",
        "static/description/screenshot_02_cron_tab.png",
    ],
    "data": [
        "security/ir.access.csv",
        "views/oski_cron_run_views.xml",
        "views/ir_cron_views.xml",
    ],
    "installable": True,
    "application": False,
}
