{
    "name": "Hidden Menus per User",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Remove menus from one specific user's screen, without creating a group or touching access rights.",
    "description": """
A user only needs part of what their role opens up to them. Rather than inventing
a group for every exception, list on their user form the menus they will no longer
see: they disappear from their screen, and theirs alone. Hiding a menu also hides
everything it contains.

This module tidies the screen, it does not lock the data: a hidden menu remains
reachable through its direct URL. To really forbid access, you need access
rights — that is the job of the OdooSkills partitioning modules.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_user_tab.png",
        "static/description/screenshot_02_menu_search.png",
    ],
    "data": ["views/res_users_views.xml"],
    "installable": True,
    "application": False,
}
