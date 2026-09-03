{
    "name": "OdooSkills — Moniteur des tâches planifiées",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Chaque exécution d'une tâche planifiée : durée, réussite, erreur, et l'historique qui va avec.",
    "description": """
Odoo garde la date du dernier passage d'une tâche planifiée dans ``lastcall``
et ne l'affiche nulle part. Le compteur d'échecs consécutifs existe lui aussi,
invisible. Résultat : une tâche qui échoue toutes les nuits ne se voit que
dans le journal du serveur, si quelqu'un pense à l'ouvrir.

Ce module inscrit chaque exécution : début, durée, réussite ou échec, et le
message d'erreur complet. L'onglet « Exécutions » de la tâche montre son
historique ; le menu « Exécutions planifiées » les montre toutes, filtrables
sur les seuls échecs.

Les échecs sont écrits sur une transaction distincte : la transaction de la
tâche est annulée quand elle échoue, et c'est précisément l'échec qu'il faut
garder.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_runs.png",
        "static/description/screenshot_02_cron_tab.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_cron_run_views.xml",
        "views/ir_cron_views.xml",
    ],
    "installable": True,
    "application": False,
}
