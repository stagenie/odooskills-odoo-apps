{
    'name': 'Treasury — Cash & Safe Management',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Treasury',
    'summary': 'Cash registers, safes, closings, transfers, configurable GL entries',
    'description': 'Complete physical treasury management: cash registers with running '
                   'balance and chained closings, safes, 9-way transfers, operation '
                   'categories, configurable accounting entries, payment integration.',
    'author': 'OdooSkills',
    'website': 'https://odooskills.com',
    'license': 'LGPL-3',
    'depends': ['account', 'mail'],
    'data': [
        'security/treasury_groups.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
}
