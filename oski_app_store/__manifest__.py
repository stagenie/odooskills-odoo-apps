{
    "name": "OdooSkills App Store",
    "version": "19.0.1.0.0",
    "category": "Website/eCommerce",
    "summary": "Boutique de modules OdooSkills (gratuits + premium)",
    "description": "Surcouche mince de website_sale exposant les modules oski_* "
                   "avec matrice multi-versions et livraison .zip.",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "security/oski_app_store_groups.xml",
        "security/ir.model.access.csv",
        "security/oski_app_store_rules.xml",
    ],
    "assets": {},
    "installable": True,
    "application": True,
}
