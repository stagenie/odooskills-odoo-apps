{
    "name": "Mass Edit",
    "version": "18.0.1.0.1",
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
        "static/description/screenshot_01_menu_actions.png",
        "static/description/screenshot_02_assistant.png",
        "static/description/screenshot_03_modeles_ouverts.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/oski_mass_edit_wizard_views.xml",
        "views/oski_mass_edit_config_views.xml",
    ],
    "installable": True,
    "application": False,
}
