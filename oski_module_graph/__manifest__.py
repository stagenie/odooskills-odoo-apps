{
    "name": "Module Dependency Graph",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "summary": "See at a glance what depends on what in your database, in SVG.",
    "description": """
The Apps list tells you what is installed. It does not tell you what holds up
what: which module would collapse if you uninstalled this one, or how many
layers separate a customization from the core.

This module draws the dependency graph of the installed modules: one level
per depth, one arrow per dependency, all in readable and printable SVG. From
a module's form, a button shows its own tree.

No third-party library, no network call: the drawing is produced by the
server.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_graph.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/oski_module_graph_views.xml",
        "views/ir_module_module_views.xml",
    ],
    "installable": True,
    "application": False,
}
