{
    "name": "OdooSkills — Journal des modifications",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Qui a créé, modifié ou supprimé quoi — sur les modèles que vous désignez, sans écrire une ligne de code.",
    "description": """
Le suivi natif d'Odoo ne couvre que les champs marqués « tracking » sur les modèles dotés d'un
chatter. Tout le reste — un prix changé sur une fiche produit, un compte bancaire réécrit, une
ligne effacée — ne laisse aucune trace.

Désignez les modèles à surveiller, choisissez les opérations (création, modification,
suppression) et, si vous le voulez, la liste des champs qui comptent. Chaque intervention est
inscrite avec son auteur, sa date, et le détail « ancienne valeur → nouvelle valeur ».

Les opérations système — installation, mise à jour, tâches planifiées — ne sont pas journalisées :
le registre garde la trace des gestes humains, pas celle de la maintenance.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_journal.png",
        "static/description/screenshot_02_regles.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_audit_rule_views.xml",
        "views/oski_audit_log_views.xml",
    ],
    "installable": True,
    "application": False,
}
