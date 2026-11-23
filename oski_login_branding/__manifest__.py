{
    "name": "Login Page Branding",
    "version": "18.0.1.0.1",
    "category": "Technical",
    "summary": "Show your brand from the login screen: custom background color, accent color and logo, without code.",
    "description": """
By default, the Odoo login page shows the framework's colors.
This module lets any administrator choose a background color,
an accent color (buttons, links) and a logo for each company
— directly from Settings, without changing the source code.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["web", "base_setup"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/res_company_views.xml",
        "views/login_templates.xml",
    ],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_login_page.png",
        "static/description/screenshot_02_settings.png",
    ],
    "installable": True,
    "application": False,
}
