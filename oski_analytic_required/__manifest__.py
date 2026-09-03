{
    "name": "OdooSkills — Analytique obligatoire par journal",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Le critère qui manque à Odoo — le journal — et le contrôle avant comptabilisation.",
    "description": """
Odoo sait déjà rendre l'analytique obligatoire : l'applicabilité des plans
analytiques l'exige par domaine d'activité, par préfixe de compte et par
catégorie d'article. Deux choses y manquent :

- le **journal**, qui est pourtant la façon dont la plupart des cabinets
  raisonnent — tout ce qui passe par le journal des achats est ventilé, le
  reste ne l'est pas ;
- le **moment** : le contrôle du cœur ne parle qu'à la comptabilisation, quand
  la saisie est finie et que l'écran affiche une erreur au lieu d'un résultat.

Ce module ajoute la règle par journal, restreignable à des préfixes de
comptes, et un écran **Écritures sans analytique** qui liste, parmi les
brouillons, les lignes qui bloqueront.

Les contreparties — comptes clients et fournisseurs — et les lignes de taxe
sont exclues d'office : elles soldent l'écriture, elles ne consomment ni ne
produisent rien.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["account"],
    "images": [
        "static/description/screenshot_01_rules.png",
        "static/description/screenshot_02_missing.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_analytic_journal_rule_views.xml",
    ],
    "installable": True,
    "application": False,
}
