{
    "name": "Portal Document Upload",
    "version": "18.0.1.0.0",
    "category": "Website/Portal",
    "summary": "Request a document from the customer: they upload it from their portal page, quotation, invoice or task.",
    "description": """
A customer can only send a file from the portal by writing a message in the
discussion thread, and only where that thread is displayed. Nothing says
what is expected of them, nothing says whether it arrived.

This module turns the process around: you are the one who asks.

- A **request** names the expected document, the record concerned, the customer
  and the due date.
- The customer sees **Requested documents** on their portal page — quotation,
  invoice, purchase order, task — and uploads their file in one move.
- The file joins the record as an attachment, the request moves to **Received**,
  and the discussion thread notifies the team.

The block hooks into the portal discussion thread: any page that displays it
gets it, with no dependency on a business module.

Accepted extensions and the maximum size are set through system parameters,
``oski_portal_upload.allowed_extensions`` and
``oski_portal_upload.max_size_mb``. A rejected file brings the customer back to
their page with the reason, never to an error page.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["portal"],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_01_portal.png",
        "static/description/screenshot_02_requests.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/oski_portal_upload_rules.xml",
        "views/oski_portal_document_request_views.xml",
        "views/portal_templates.xml",
    ],
    "installable": True,
    "application": False,
}
