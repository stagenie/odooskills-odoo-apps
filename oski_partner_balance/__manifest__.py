{
    'name': 'Partner Balance — Customer & Vendor Statement',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Chronological partner statement with running balance, opening '
               'balance, journal filters and PDF/XLSX output.',
    'description': """
Odoo Community has no partner ledger. This module adds one.

- Chronological statement per customer and/or vendor, with a running balance
  on every single line.
- Optional opening balance: the balance carried forward at the start date.
- Include or exclude journals.
- Exclude a specific invoice or payment from the computation.
- Customer only, vendor only, both side by side, or netted into one balance
  when the same partner is both.
- PDF and XLSX output from the very same data as the screen.
""",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'support': 'support@odooskills.com',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'security/partner_balance_groups.xml',
        'security/ir.model.access.csv',
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
