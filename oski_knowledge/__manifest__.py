{
    'name': 'Connaissances',
    'version': '19.0.1.0.0',
    'category': 'Productivity/Knowledge',
    'summary': "Base de connaissances hiérarchique : articles arbre, éditeur "
               "riche, espaces partagé/privé, favoris, corbeille, recherche",
    'description': "Base de connaissances type Notion pour Odoo 19 CE : "
                   "articles hiérarchiques illimités rédigés dans l'éditeur "
                   "HTML natif d'Odoo, espace de travail partagé et espace "
                   "privé, favoris ordonnés, corbeille, navigation par sidebar.",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'support': 'support@odooskills.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'web', 'web_tour'],
    'data': [
        'security/knowledge_security.xml',
        'security/ir.model.access.csv',
        'security/knowledge_rules.xml',
        'views/knowledge_article_views.xml',
        'views/knowledge_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'oski_knowledge/static/src/knowledge_app/**/*',
        ],
        'web.assets_tests': [
            'oski_knowledge/static/tests/tours/**/*',
        ],
    },
    'installable': True,
    'application': True,
}
