{
    'name': 'Location — Gestion de location générique',
    'version': '19.0.1.0.0',
    'category': 'Services/Rental',
    'summary': "Louez tout type de ressource : véhicules, salles, engins, matériel",
    'description': "Gestion de location générique : ressources unitaires, réservations, "
                   "départ/retour avec état des lieux, caution, facturation, alertes retard.",
    'author': 'OdooSkills',
    'website': 'https://odooskills.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'account', 'product'],
    'data': [
        'security/rental_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/product_data.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
}
