{
    "name": "OdooSkills — Rappel de saisie des temps",
    "version": "19.0.1.0.0",
    "category": "Services/Timesheets",
    "summary": "Le tableau des retards de saisie, semaine par semaine, et le rappel qui va avec.",
    "description": """
Odoo Community ne rappelle rien : une feuille de temps vide le reste, et le
chef de projet s'en aperçoit à la facturation, quand plus personne ne se
souvient de ce qu'il a fait trois semaines plus tôt.

Ce module compare chaque semaine les heures saisies aux heures attendues :

- l'horaire de travail de l'employé fait foi — un mi-temps relevé sur 35
  heures serait en retard toutes les semaines — et le réglage de la société
  n'est qu'un recours ;
- une **tolérance** évite de déranger pour un quart d'heure ;
- le retard devient une **donnée** : il se relit, se totalise et se compare
  d'une semaine à l'autre, en liste comme en tableau croisé ;
- l'employé reçoit une **activité**, jamais un courriel, et une seule fois par
  semaine relevée.

La tâche planifiée relève la semaine **écoulée**, du lundi au dimanche :
relever la semaine en cours accuserait tout le monde d'un retard qui n'existe
pas encore.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["hr_timesheet"],
    "images": [
        "static/description/screenshot_01_gaps.png",
        "static/description/screenshot_02_settings.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/oski_timesheet_gap_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
