{
    'name': "Knowledge Base",
    'version': '20.0.1.0.0',
    'category': 'Productivity/Knowledge',
    'summary': "Hierarchical knowledge base: article tree, rich editor, shared/private spaces, favorites, trash, search",
    'description': "Notion-style knowledge base for Odoo 19 CE: unlimited hierarchical articles written in Odoo's native HTML editor, shared workspace and private space, ordered favorites, trash, sidebar navigation.",
    'author': 'OdooSkills',
    'website': 'https://apps.odooskills.com',
    'support': 'apps@odooskills.com',
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
    'depends': ['base', 'mail', 'web', 'web_tour'],
    'data': [
        'security/knowledge_security.xml',
        'security/ir.access.csv',
        'views/knowledge_article_views.xml',
        'views/knowledge_menus.xml',
    ],
    'demo': [
        'demo/knowledge_demo.xml',
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
