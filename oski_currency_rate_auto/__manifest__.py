{
    "name": "Automatic Currency Rates",
    "version": "20.0.1.0.0",
    "category": "Accounting",
    "summary": "Exchange rates update on their own, from the European Central Bank.",
    "description": """
Odoo Community can keep a table of exchange rates; it cannot fill it. So
every morning someone copies rates by hand, or nobody does and conversions
drift silently.

A daily scheduled action fetches the reference rates published by the
European Central Bank and records them for each company that asked for it.
Inactive currencies are left aside; the company's currency is the pivot,
whatever it is.

No API key, no account to open: the ECB publishes its rates freely. A
network failure is recorded on the company and does not interrupt the
others.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_company.png",
        "static/description/screenshot_02_rates.png",
    ],
    "data": [
        "data/ir_cron.xml",
        "views/res_company_views.xml",
    ],
    "installable": True,
    "application": False,
}
