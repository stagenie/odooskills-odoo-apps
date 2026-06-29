{
    "name": "OdooSkills — QR vCard Contact",
    "version": "19.0.1.0.0",
    "category": "Contacts",
    "summary": "Partagez un contact Odoo en un scan : le QR code vCard se génère automatiquement sur la fiche.",
    "description": """
Fini la saisie manuelle des coordonnées en réunion ou en salon.
Ce module ajoute un onglet "QR vCard" sur chaque fiche contact Odoo.
L'interlocuteur scanne le code avec son téléphone et le contact (nom, société,
fonction, e-mail, téléphone, site web) s'ajoute à son carnet d'adresses
en un tap — aucune application tierce requise.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
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
