{
    "name": "OdooSkills — Devis périmés",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Les devis échus s'annulent d'eux-mêmes, et le vendeur est relancé avant l'échéance.",
    "description": """
Odoo calcule une date de validité sur chaque devis, sait dire qu'il est
expiré… et n'en fait rien. Les devis morts s'empilent dans le tunnel, faussent
les prévisions et le montant du pipeline, et personne ne les rouvre jamais.

Ce module ferme la boucle :

- une **relance** au vendeur, sous forme d'activité, quelques jours avant
  l'échéance — le délai est réglable, et jamais un courriel de plus ;
- une **péremption** automatique des devis dont la date de validité est
  dépassée, avec une note au dossier qui dit pourquoi et quand.

Les deux réglages sont indépendants et vivent sur la société : une filiale qui
vend à la semaine et une maison mère qui vend au trimestre n'ont pas le même
rythme.

La relance passe **avant** la péremption dans la même nuit : un devis relancé
le matin puis annulé le soir ferait passer le vendeur pour un menteur.

Les devis verrouillés ne sont jamais touchés.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["sale"],
    "images": [
        "static/description/screenshot_01_expired.png",
        "static/description/screenshot_02_settings.png",
    ],
    "data": [
        "data/ir_cron.xml",
        "views/sale_order_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
