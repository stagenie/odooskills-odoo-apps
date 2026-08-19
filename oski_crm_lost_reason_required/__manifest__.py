{
    "name": "OdooSkills — Motif de perte obligatoire",
    "version": "19.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Aucune opportunité perdue sans motif, et ce que chaque motif coûte vraiment.",
    "description": """
Dans Odoo, le motif de perte est facultatif : l'assistant l'affiche, personne
n'est obligé de le remplir. Six mois plus tard, la moitié du pipeline perdu
est sans explication, et la question « pourquoi perdons-nous ? » n'a pas de
réponse chiffrée.

Ce module :

- rend le **motif obligatoire**, au niveau du modèle et pas seulement de
  l'écran — un import, une action serveur ou un appel direct sont soumis à la
  même règle ;
- exige au besoin une **note de clôture**, quelques mots de contexte pour
  celui qui reprendra ce client dans un an ;
- ajoute à chaque motif le **revenu perdu** et la date de la dernière perte,
  totalisés dans la liste.

Odoo compte les opportunités par motif ; il ne dit pas ce que chacun emporte.
« Prix trop élevé » sur deux affaires de mille euros et sur une de deux cent
mille n'appelle pas la même réaction.

Les deux exigences se règlent par société, dans les paramètres du CRM.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["crm"],
    "images": [
        "static/description/screenshot_01_reasons.png",
        "static/description/screenshot_02_wizard.png",
    ],
    "data": [
        "views/crm_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
