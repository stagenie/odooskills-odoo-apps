from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestAccessA25(TransactionCase):
    """Points de contrôle A25 : pas d'énumération par id d'un article privé
    d'autrui (favori, enfant), déplacement vers un parent inaccessible."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Article = cls.env['knowledge.article']
        cls.user_a = new_test_user(cls.env, login='ka25_a', groups='base.group_user')
        cls.user_b = new_test_user(cls.env, login='ka25_b', groups='base.group_user')
        cls.priv_a = cls.Article.create({
            'name': 'Secret de A', 'section': 'private', 'owner_id': cls.user_a.id})
        cls.ws_b = cls.Article.with_user(cls.user_b).create(
            {'name': 'Note de B', 'section': 'workspace'})

    def test_favorite_on_unreadable_article_refused(self):
        # Sans garde, B crée un favori sur l'id d'un privé de A et lit son
        # titre via article_id (display_name lu en sudo par le Many2one).
        Fav = self.env['knowledge.article.favorite'].with_user(self.user_b)
        with self.assertRaises(AccessError):
            Fav.create({'article_id': self.priv_a.id})

    def test_favorite_retarget_to_unreadable_article_refused(self):
        self.ws_b.with_user(self.user_b).action_toggle_favorite()
        fav = self.env['knowledge.article.favorite'].with_user(self.user_b).search([])
        self.assertEqual(len(fav), 1)
        with self.assertRaises(AccessError):
            fav.write({'article_id': self.priv_a.id})

    def test_create_child_under_unreadable_parent_refused(self):
        # Sans garde, l'enfant hérite de section=private, owner=B : la règle
        # de création passe et B lit le titre du parent privé de A.
        with self.assertRaises(AccessError):
            self.Article.with_user(self.user_b).create(
                {'name': 'Intrus', 'parent_id': self.priv_a.id})

    def test_move_under_unreadable_parent_refused(self):
        with self.assertRaises(AccessError):
            self.ws_b.with_user(self.user_b).write({'parent_id': self.priv_a.id})
        with self.assertRaises(AccessError):
            self.ws_b.with_user(self.user_b).action_move_to(parent_id=self.priv_a.id)
        self.assertFalse(self.ws_b.parent_id)

    def test_owner_can_create_child_in_own_private(self):
        child = self.Article.with_user(self.user_a).create(
            {'name': 'Sous-secret', 'parent_id': self.priv_a.id})
        self.assertEqual(child.section, 'private')
        self.assertEqual(child.owner_id, self.user_a)

    def test_private_hidden_from_full_text_and_read_group(self):
        self.priv_a.body = '<p>motclefconfidentiel</p>'
        Article = self.Article.with_user(self.user_b)
        self.assertFalse(Article.search([('body_text', 'ilike', 'motclefconfidentiel')]))
        groups = Article._read_group(
            [('section', '=', 'private')], ['owner_id'], ['__count'])
        self.assertNotIn(self.user_a, [owner for owner, _count in groups])
        self.assertFalse(Article.search_count([('owner_id', '=', self.user_a.id)]))

    def test_child_follows_private_parent_even_if_section_posted(self):
        # Une section 'workspace' postée avec un parent privé ne doit pas
        # exposer l'enfant à tous.
        child = self.Article.with_user(self.user_a).create({
            'name': 'Sous-secret', 'parent_id': self.priv_a.id, 'section': 'workspace'})
        self.assertEqual(child.section, 'private')
        self.assertFalse(self.Article.with_user(self.user_b).search([('id', '=', child.id)]))
