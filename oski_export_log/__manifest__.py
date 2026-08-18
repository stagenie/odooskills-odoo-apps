{
    "name": "OdooSkills — Journal des exports",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Sachez qui sort quelles données de votre base : modèle, champs, nombre de lignes, date.",
    "description": """
Odoo ne propose qu'un interrupteur : le groupe « Autoriser l'export » est donné, ou il ne l'est
pas. Une fois donné, plus rien n'est su — ni quel modèle a été vidé, ni combien de lignes sont
sorties, ni quand.

Ce module inscrit chaque export réellement exécuté : l'auteur, le modèle, la liste des champs
demandés et le nombre de lignes produites. Il n'empêche rien et ne ralentit rien ; il rend
visible ce qui sort.

Les exports refusés faute de droits ne produisent aucune ligne : le journal ne recense que ce qui
a réellement quitté la base.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_journal.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_export_log_views.xml",
    ],
    "installable": True,
    "application": False,
}
