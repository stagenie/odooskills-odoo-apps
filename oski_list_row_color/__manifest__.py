{
    "name": "OdooSkills — Couleur de lignes de liste",
    "version": "17.0.1.0.0",
    "category": "Technical",
    "summary": "Colorer les lignes des listes selon une règle, sans code",
    "description": """
Définissez des règles « si <expression> alors couleur » par modèle. Le module
génère automatiquement une vue liste héritée appliquant la décoration Bootstrap
correspondante (info, succès, avertissement, danger, etc.). Aucun code requis.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_row_color_rule_views.xml",
    ],
    "installable": True,
    "application": False,
}
