from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestArticleSearch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Article = cls.env['knowledge.article']
        cls.a1 = cls.Article.create({
            'name': 'Procédure congés', 'section': 'workspace',
            'body': '<p>Demande via le portail RH.</p>'})
        cls.a2 = cls.Article.create({
            'name': 'FAQ', 'section': 'workspace',
            'body': '<p>Mot de passe oublié : contacter le support.</p>'})

    def test_search_view_loads(self):
        # La vue search se parse sans erreur (fields_view_get).
        self.env['knowledge.article'].get_view(
            self.env.ref('oski_knowledge.view_article_search').id, 'search')

    def test_filter_domain_matches_name(self):
        found = self.Article.search(
            ['|', ('name', 'ilike', 'congés'), ('body_text', 'ilike', 'congés')])
        self.assertIn(self.a1, found)
        self.assertNotIn(self.a2, found)

    def test_filter_domain_matches_body_text(self):
        found = self.Article.search(
            ['|', ('name', 'ilike', 'support'), ('body_text', 'ilike', 'support')])
        self.assertIn(self.a2, found)
        self.assertNotIn(self.a1, found)
