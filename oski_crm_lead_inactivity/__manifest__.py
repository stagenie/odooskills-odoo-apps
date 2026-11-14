# -*- coding: utf-8 -*-
{
    "name": "CRM Dormant Leads",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Spot forgotten opportunities: highlighting, a day counter and a dormant filter in your CRM pipeline.",
    "description": """
CRM Dormant Leads
=================

Highlights leads and opportunities that have seen no movement for a
configurable number of days. Ideal for following up on forgotten deals in
the pipeline.

The inactivity threshold is set in the CRM Settings. A "Days inactive"
column and row highlighting appear in the pipeline, and a "Dormant" filter
isolates the deals to follow up on.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["crm"],
    "data": [
        "views/crm_lead_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "images": ["static/description/screenshot_02_pipeline_dormantes.png"],
    "installable": True,
    "application": False,
}
