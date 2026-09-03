{
    "name": "OdooSkills — Moniteur de la file de courriels",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Sachez que vos courriels ne partent plus le jour même, pas trois mois après.",
    "description": """
Un serveur sortant mal configuré ne fait pas de bruit : les courriels
s'empilent en ``mail.mail``, la file grossit, et personne ne l'apprend avant
qu'un client demande pourquoi il n'a rien reçu. Odoo sait renvoyer un courriel
en échec, mais ne surveille rien.

Ce module ausculte la file tous les jours : combien en attente, combien en
échec, depuis combien de temps le plus vieux courriel attend, et pour quelles
causes. Le verdict est inscrit, et une activité est posée aux administrateurs
quand la file se dégrade.

L'alerte ne passe pas par un courriel — ce serait demander au malade de porter
lui-même son diagnostic.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["mail"],
    "images": [
        "static/description/screenshot_01_checks.png",
        "static/description/screenshot_02_failed.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/oski_mail_queue_check_views.xml",
    ],
    "installable": True,
    "application": False,
}
