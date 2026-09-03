{
    "name": "OdooSkills — Menus masqués par utilisateur",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Retirez des menus de l'écran d'un utilisateur précis, sans créer de groupe ni toucher aux droits.",
    "description": """
Un utilisateur n'a besoin que d'une partie de ce que son rôle lui ouvre. Plutôt que d'inventer un
groupe pour chaque exception, désignez sur sa fiche les menus qu'il ne verra plus : ils
disparaissent de son écran, et de lui seul. Masquer un menu masque aussi tout ce qu'il contient.

Ce module range l'écran, il ne verrouille pas la donnée : un menu masqué reste atteignable par
son adresse directe. Pour interdire réellement l'accès, il faut des droits — c'est le rôle des
modules de cloisonnement OdooSkills.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_onglet_utilisateur.png",
        "static/description/screenshot_02_choix_des_menus.png",
    ],
    "data": ["views/res_users_views.xml"],
    "installable": True,
    "application": False,
}
