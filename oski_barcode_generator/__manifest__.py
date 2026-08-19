{
    "name": "OdooSkills — Codes-barres EAN13 en masse",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Attribuez des codes EAN13 valides à tous les articles qui n'en ont pas, d'un geste.",
    "description": """
Odoo sait vérifier un code-barres et en calculer la clé ; il ne sait pas en
produire. Un catalogue de mille références sans code se remplit donc à la
main, un article après l'autre, avec les fautes de frappe que cela suppose.

Ce module attribue des **EAN13 valides**, clé de contrôle comprise :

- depuis la liste des articles ou des variantes, sur la sélection ;
- ou sur **tous** les articles qui n'ont pas encore de code.

Le préfixe par défaut commence par 2 : la plage 20-29 est celle que la norme
réserve à l'usage interne d'une entreprise. Y déroger produirait des codes
ressemblant à ceux d'un autre fabricant.

Les articles qui portent déjà un code ne sont **jamais** touchés — écraser un
code casserait les étiquettes imprimées et les scanners qui les lisent. Les
numéros déjà pris dans la plage sont sautés, y compris ceux venus d'un import.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["product"],
    "images": [
        "static/description/screenshot_01_wizard.png",
        "static/description/screenshot_02_products.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_barcode_generator_views.xml",
    ],
    "installable": True,
    "application": False,
}
