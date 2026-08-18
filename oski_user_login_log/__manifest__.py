{
    "name": "OdooSkills — Journal des connexions",
    "version": "19.0.1.0.0",
    "category": "Technical",
    "summary": "Chaque connexion et chaque échec, avec son identifiant, son adresse IP et sa date.",
    "description": """
Odoo retient la date de dernière connexion et rien d'autre : ni les tentatives échouées, ni les
adresses d'où l'on entre. Les échecs partent dans le fichier de journal du serveur, que personne
n'ouvre — et qui disparaît à la rotation.

Ce module tient un registre consultable depuis l'interface : identifiant saisi, utilisateur
reconnu s'il y en a un, réussite ou échec, adresse IP, date. Une rafale d'échecs sur un même
identifiant se voit alors d'un coup d'œil.

Les échecs sont écrits sur une transaction propre : une tentative refusée annule tout le reste,
et une trace posée dans la transaction de la connexion disparaîtrait avec elle.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "images": [
        "static/description/screenshot_01_journal.png",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/oski_login_log_views.xml",
    ],
    "installable": True,
    "application": False,
}
