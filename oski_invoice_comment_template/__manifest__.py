{
    "name": "Invoice Comment Templates",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "No more copy-paste: a library of approved notes, inserted on the invoice in one click and printed in the PDF.",
    "description": """
Late payment penalties, early payment discount, VAT legal notices: no need to retype them on every invoice.
This module adds a library of comment templates (rich HTML) that can be selected directly
on the invoice form. The chosen comment is automatically copied into the Odoo narration,
printed natively in the PDF — no QWeb report change required.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "images": ["static/description/screenshot_01_config_modeles.png"],
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_invoice_comment_template_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
}
