{
    "name": "List Row Colors",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Highlight your Odoo lists according to your business rules — without touching a single line of code.",
    "description": """
Spot your urgent orders, overdue invoices or critical products at a glance.
Define a Python condition (e.g. state == 'done'), pick a color (red, green,
orange…) and the module automatically generates the inherited list view — no XML to edit.
Works on any Odoo model, Community or Enterprise.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_row_color_rule_views.xml",
    ],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_colored_quotations.png",
        "static/description/screenshot_02_rule_form.png",
        "static/description/screenshot_03_rules.png",
    ],
    "installable": True,
    "application": False,
}
