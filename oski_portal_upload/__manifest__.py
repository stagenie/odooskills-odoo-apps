{
    "name": "OdooSkills — Dépôt de documents au portail",
    "version": "19.0.1.0.0",
    "category": "Website/Portal",
    "summary": "Demandez un document au client : il le dépose depuis sa page portail, devis, facture ou tâche.",
    "description": """
Un client ne peut envoyer un fichier depuis le portail qu'en écrivant un
message dans le fil de discussion, et seulement là où ce fil est affiché.
Rien ne dit ce qu'on attend de lui, rien ne dit si c'est arrivé.

Ce module renverse la démarche : c'est vous qui demandez.

- Une **demande** nomme le document attendu, la fiche concernée, le client et
  l'échéance.
- Le client voit **Documents attendus** sur sa page portail — devis, facture,
  bon de commande, tâche — et dépose son fichier en un geste.
- Le fichier rejoint la fiche en pièce jointe, la demande passe à **Reçu**, et
  le fil de discussion le signale à l'équipe.

Le bloc se greffe sur le fil de discussion du portail : toute page qui
l'affiche l'obtient, sans dépendance à un module métier.

Les extensions acceptées et le poids maximal se règlent par paramètres
système, ``oski_portal_upload.allowed_extensions`` et
``oski_portal_upload.max_size_mb``. Un fichier refusé ramène le client sur sa
page avec la raison, jamais sur une page d'erreur.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "support@odooskills.com",
    "license": "LGPL-3",
    "depends": ["portal"],
    "images": [
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
