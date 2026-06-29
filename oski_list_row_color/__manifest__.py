{
    "name": "OdooSkills — Couleur de lignes de liste",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Surlignez vos listes Odoo selon vos règles métier — sans toucher une seule ligne de code.",
    "description": """
Repérez en un coup d'œil vos commandes urgentes, factures en retard ou articles critiques.
Définissez une condition Python (ex : state == 'done'), choisissez une couleur (rouge, vert,
orange…) et le module génère automatiquement la vue liste héritée — aucun XML à modifier.
Fonctionne sur n'importe quel modèle Odoo, Community ou Enterprise.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_row_color_rule_views.xml",
    ],
    "images": [
        "static/description/screenshot_01_sale_orders_colored.png",
        "static/description/screenshot_02_rule_form_config.png",
        "static/description/screenshot_03_rules_list.png",
    ],
    "installable": True,
    "application": False,
}
