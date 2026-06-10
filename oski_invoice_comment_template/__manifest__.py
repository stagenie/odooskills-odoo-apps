{
    "name": "OdooSkills — Modèles de remarque sur factures",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Insérez des remarques réutilisables dans la note des factures (imprimées dans le PDF)",
    "description": """
Modèles de remarques réutilisables pour les factures clients et fournisseurs.
La remarque sélectionnée est recopiée dans la note de la facture (narration),
qui est imprimée nativement dans le PDF — aucun héritage de rapport requis.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_invoice_comment_template_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
}
