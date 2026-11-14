{
    "name": "Mandatory Analytic",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "The criterion Odoo lacks — the journal — and the check before posting.",
    "description": """
Odoo can already make analytic mandatory: analytic plan applicability
requires it by business domain, by account prefix and by
product category. Two things are missing:

- the **journal**, which is how most accounting firms actually
  think — everything going through the purchase journal is distributed, the
  rest is not;
- the **timing**: the core check only speaks up at posting, when
  data entry is finished and the screen shows an error instead of a result.

This module adds the rule per journal, which can be restricted to account
prefixes, and an **Entries Without Analytic** screen that lists, among
drafts, the lines that will block.

Counterpart lines — receivable and payable accounts — and tax lines
are excluded by default: they balance the entry, they neither consume nor
produce anything.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
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
