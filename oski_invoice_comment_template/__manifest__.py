{
    "name": "OdooSkills — Modèles de remarque sur factures",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Fini les copier-coller : une bibliothèque de mentions validées, insérables en un clic sur la facture et imprimées dans le PDF.",
    "description": """
Pénalités de retard, escompte, mentions légales TVA : plus besoin de les retaper à chaque facture.
Ce module ajoute une bibliothèque de modèles de remarques (HTML riche) sélectionnables directement
sur le formulaire de facture. La remarque choisie se copie automatiquement dans la narration Odoo,
imprimée nativement dans le PDF — aucune modification de rapport QWeb requise.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "images": ["static/description/screenshot_01_config_modeles.png"],
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_invoice_comment_template_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
}
