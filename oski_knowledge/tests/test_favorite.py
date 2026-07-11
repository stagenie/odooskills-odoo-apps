from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestFavorite(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Article = cls.env['knowledge.article']
        cls.user_a = new_test_user(
            cls.env, login='kn_a', groups='base.group_user')
        cls.user_b = new_test_user(
            cls.env, login='kn_b', groups='base.group_user')
        cls.art = cls.Article.create({'name': 'Partagé', 'section': 'workspace'})

    def test_toggle_creates_and_removes(self):
        art = self.art.with_user(self.user_a)
        self.assertFalse(art.is_user_favorite)
        art.action_toggle_favorite()
        self.env.invalidate_all()
        self.assertTrue(art.is_user_favorite)
        art.action_toggle_favorite()
        self.env.invalidate_all()
        self.assertFalse(art.is_user_favorite)

    def test_favorite_is_per_user(self):
        self.art.with_user(self.user_a).action_toggle_favorite()
        self.env.invalidate_all()
        self.assertTrue(self.art.with_user(self.user_a).is_user_favorite)
        self.assertFalse(self.art.with_user(self.user_b).is_user_favorite)

    def test_search_is_user_favorite(self):
        self.art.with_user(self.user_a).action_toggle_favorite()
        self.env.invalidate_all()
        found = self.Article.with_user(self.user_a).search(
            [('is_user_favorite', '=', True)])
        self.assertIn(self.art, found)
        found_b = self.Article.with_user(self.user_b).search(
            [('is_user_favorite', '=', True)])
        self.assertNotIn(self.art, found_b)

    def test_user_sees_only_own_favorites(self):
        self.art.with_user(self.user_a).action_toggle_favorite()
        self.env.invalidate_all()
        Fav = self.env['knowledge.article.favorite']
        self.assertEqual(
            len(Fav.with_user(self.user_a).search([])), 1)
        self.assertEqual(
            len(Fav.with_user(self.user_b).search([])), 0)
