{
    "name": "Required Lost Reason",
    "version": "19.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "No opportunity lost without a reason, and what each reason really costs.",
    "description": """
In Odoo, the lost reason is optional: the wizard shows it, nobody is required
to fill it in. Six months later, half of the lost pipeline has no
explanation, and the question "why are we losing?" has no answer in figures.

This module:

- makes the **reason required**, at the model level and not just on screen
  — an import, a server action or a direct call are subject to the same
  rule;
- optionally requires a **closing note**, a few words of context for
  whoever takes over this customer a year from now;
- adds to each reason the **lost revenue** and the date of the last loss,
  totaled in the list.

Odoo counts opportunities per reason; it does not say what each one takes
away. "Too expensive" on two deals of a thousand euros and on one of two
hundred thousand does not call for the same response.

Both requirements are set per company, in the CRM settings.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["crm"],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_reasons.png",
        "static/description/screenshot_02_wizard.png",
        "static/description/screenshot_03_settings.png",
    ],
    "data": [
        "views/crm_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
