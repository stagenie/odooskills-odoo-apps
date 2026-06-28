{
    "name": "Abonnements — Oski",
    "version": "19.0.1.0.0",
    "category": "Sales/Subscriptions",
    "summary": "Facturation récurrente d'abonnements (Community) : plans, cron, MRR",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "license": "LGPL-3",
    "depends": ["sale", "account"],
    "data": [
        "security/subscription_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
    ],
    "installable": True,
    "application": True,
}
