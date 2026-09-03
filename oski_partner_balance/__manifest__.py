{
    "name": "Partner Balance",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "The statement Community lacks: running balance line by line, opening balance, journal filters, PDF and Excel export.",
    "description": """Odoo Community can show what a customer owes in total, but not how it got
there. This module adds the account statement: every invoice, every credit
note, every payment in order, with the running balance recalculated on
every line.

- Chronological statement by customer, by supplier, or both.
- Opening balance: the balance at the start date, as a single opening line.
- Inclusion or exclusion of journals.
- Exclusion of a specific invoice or payment from the computation.
- Four scopes: customer only, supplier only, both side by side, or netted
  into a single balance when the partner is both at once.
- PDF and Excel export from the data shown on screen, not a second
  computation.""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "images": ["static/description/banner.png"],
    "depends": ["account"],
    "data": [
        "security/partner_balance_groups.xml",
        "security/ir.model.access.csv",
        "security/partner_balance_rules.xml",
        "views/account_move_views.xml",
        "views/partner_balance_wizard_views.xml",
        "views/partner_balance_line_views.xml",
        "views/menu_views.xml",
        "reports/partner_balance_report.xml",
    ],
    "installable": True,
    "application": False,
    "post_init_hook": "post_init_hook",
}
