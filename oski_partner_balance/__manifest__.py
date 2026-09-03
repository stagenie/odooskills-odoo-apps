{
    'name': 'OdooSkills — Solde tiers : relevé client et fournisseur',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Le relevé de compte qui manque à la Communauté : solde cumulé '
               'ligne à ligne, report à nouveau, filtres de journaux, PDF et Excel.',
    'description': """
Odoo Community sait afficher ce qu'un client doit au total, mais pas comment
on en est arrivé là. Ce module ajoute le relevé de compte : chaque facture,
chaque avoir, chaque règlement dans l'ordre, avec le solde cumulé recalculé
sur chaque ligne.

- Relevé chronologique par client, par fournisseur, ou les deux.
- Report à nouveau : le solde à la date de début, en une ligne d'ouverture.
- Inclusion ou exclusion de journaux.
- Exclusion d'une facture ou d'un règlement précis du calcul.
- Quatre portées : client seul, fournisseur seul, les deux côte à côte, ou
  compensés en un solde net quand le tiers est les deux à la fois.
- Sortie PDF et Excel à partir des données affichées à l'écran, pas d'un
  second calcul.
""",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'support': 'support@odooskills.com',
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
    'depends': ['account'],
    'data': [
        'security/partner_balance_groups.xml',
        'security/ir.model.access.csv',
        'security/partner_balance_rules.xml',
        'views/account_move_views.xml',
        'views/partner_balance_wizard_views.xml',
        'views/partner_balance_line_views.xml',
        'views/menu_views.xml',
        'reports/partner_balance_report.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
}
