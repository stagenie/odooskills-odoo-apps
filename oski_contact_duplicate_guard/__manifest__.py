{
    "name": "Contact Duplicate Guard",
    "version": "19.0.1.0.0",
    "category": "Contacts",
    "summary": "Avoid duplicate customers: get an alert as soon as an email or phone number already exists.",
    "description": """
Warns the user at entry time when a contact shares the same email or the
same phone number as an existing contact. Detection is non-blocking: the
contact can be created, but a banner and a link to the possible duplicate
are displayed. Email and phone detection can be enabled separately from the
Settings.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["contacts", "base_setup"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
    ],
    "images": [
        "static/description/screenshot_01_bandeau_doublon.png",
        "static/description/screenshot_02_alerte_email_doublon.png",
        "static/description/screenshot_03_liste_doublons.png",
    ],
    "installable": True,
    "application": False,
}
