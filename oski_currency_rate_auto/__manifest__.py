{
    "name": "OdooSkills — Taux de change automatiques",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "summary": "Les taux de change se mettent à jour tout seuls, depuis la Banque centrale européenne.",
    "description": """
Odoo Community sait tenir un tableau de taux de change ; il ne sait pas le
remplir. Chaque matin, quelqu'un recopie donc des taux à la main, ou personne
ne le fait et les conversions dérivent en silence.

Une tâche planifiée quotidienne va chercher les taux de référence publiés par
la Banque centrale européenne et les inscrit pour chaque société qui l'a
demandé. Les devises inactives sont laissées de côté ; celle de la société sert
de pivot, quelle qu'elle soit.

Aucune clé d'interface, aucun compte à ouvrir : la BCE publie ses taux
librement. Une panne réseau est inscrite sur la société et n'interrompt pas les
autres.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_company.png",
        "static/description/screenshot_02_rates.png",
    ],
    "data": [
        "data/ir_cron.xml",
        "views/res_company_views.xml",
    ],
    "installable": True,
    "application": False,
}
