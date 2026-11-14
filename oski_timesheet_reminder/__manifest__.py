{
    "name": "Timesheet Reminder",
    "version": "18.0.1.0.0",
    "category": "Services/Timesheets",
    "summary": "The table of missing timesheet hours, week by week, and the reminder that goes with it.",
    "description": """
Odoo Community sends no reminders: an empty timesheet stays empty, and the
project manager notices at invoicing time, when nobody remembers anymore
what they did three weeks earlier.

Every week, this module compares the hours logged with the hours expected:

- the employee's working schedule is the reference — a part-timer checked
  against 35 hours would be behind every single week — and the company
  setting is only a fallback;
- a **tolerance** avoids bothering anyone over fifteen minutes;
- missing hours become **data**: they can be reviewed, totaled and compared
  from one week to the next, in list and pivot views alike;
- the employee receives an **activity**, never an email, and only once per
  week checked.

The scheduled action checks the **past** week, Monday to Sunday:
checking the current week would accuse everyone of a delay that does not
exist yet.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["hr_timesheet"],
    "images": [
        "static/description/screenshot_01_gaps.png",
        "static/description/screenshot_02_settings.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/oski_timesheet_gap_rules.xml",
        "data/ir_cron.xml",
        "views/oski_timesheet_gap_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
