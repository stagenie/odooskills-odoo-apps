{
    "name": "QR vCard Contact",
    "version": "19.0.1.0.0",
    "category": "Contacts",
    "summary": "Share an Odoo contact with a single scan: the vCard QR code is generated automatically on the contact form.",
    "description": """
No more typing contact details by hand in meetings or at trade shows.
This module adds a "QR vCard" tab to every Odoo contact form.
The other person scans the code with their phone and the contact (name, company,
job position, email, phone, website) is added to their address book
in one tap — no third-party app required.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["contacts"],
    "external_dependencies": {"python": ["qrcode"]},
    "data": [
        "views/res_partner_views.xml",
    ],
    "images": ["static/description/screenshot_01_qr_vcard_tab.png"],
    "installable": True,
    "application": False,
}
