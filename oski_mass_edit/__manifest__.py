{
    "name": "Mass Edit",
    "version": "20.0.1.0.2",
    "category": "Technical",
    "summary": "Change a field on an entire selection from the list view, without going through each record.",
    "description": """
Select records in any list view, open "Mass Edit" from the Actions menu,
choose the field and the value: all selected records are updated at once.
An administrator declares the relevant models once; the menu entry then
appears in their list view. Odoo's access rights and record rules apply
normally — the module never writes in sudo.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_actions_menu.png",
        "static/description/screenshot_02_wizard.png",
        "static/description/screenshot_03_enabled_models.png",
    ],
    "data": [
        "security/ir.access.csv",
        "wizards/oski_mass_edit_wizard_views.xml",
        "views/oski_mass_edit_config_views.xml",
    ],
    "installable": True,
    "application": False,
}
