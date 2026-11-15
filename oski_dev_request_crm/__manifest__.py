{
    "name": "Development Request — CRM Opportunities",
    "version": "19.0.2.0.0",
    "category": "Website",
    "summary": "Each module request opens an opportunity in the sales pipeline.",
    "description": """
A development request is first a deal to win. This bridge creates the matching
CRM opportunity as soon as the public form is submitted, with the contact, the
need, the target Odoo version and the stated budget — without removing the
request from its own technical pipeline.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["oski_dev_request", "crm"],
    "data": [
        "views/oski_dev_request_views.xml",
    ],
    "auto_install": True,
    "installable": True,
}
