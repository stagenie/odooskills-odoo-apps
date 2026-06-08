{
    "name": "OdooSkills — QR vCard Contact",
    "version": "16.0.1.0.0",
    "category": "Contacts",
    "summary": "Code QR vCard automatique sur la fiche contact",
    "description": """
Génère automatiquement un code QR au format vCard 3.0 sur chaque fiche contact.
Scanné avec un smartphone, il ajoute le contact (nom, société, fonction, email,
téléphone, mobile, site web) au carnet d'adresses sans saisie manuelle.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["contacts"],
    "external_dependencies": {"python": ["qrcode"]},
    "data": [
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
