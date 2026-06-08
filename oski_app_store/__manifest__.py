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
        "data/oski_module_category_data.xml",
        "data/oski_module_tag_demo.xml",
        "views/oski_module_category_views.xml",
        "views/oski_module_tag_views.xml",
        "views/oski_module_views.xml",
        "views/product_template_views.xml",
        "views/oski_app_store_menus.xml",
        "templates/catalog_templates.xml",
        "templates/module_page_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "oski_app_store/static/src/scss/oski_store_chrome.scss",
            "oski_app_store/static/src/scss/oski_app_store.scss",
        ],
    },
    "installable": True,
    "application": True,
}
