from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestArticleRules(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Article = cls.env['knowledge.article']
        cls.user_a = new_test_user(cls.env, login='kr_a', groups='base.group_user')
        cls.user_b = new_test_user(cls.env, login='kr_b', groups='base.group_user')
        cls.manager = new_test_user(
            cls.env, login='kr_m',
            groups='base.group_user,oski_knowledge.group_knowledge_manager')
        cls.ws = cls.Article.create({'name': 'WS', 'section': 'workspace'})
        cls.priv_a = cls.Article.create({
            'name': 'Privé A', 'section': 'private', 'owner_id': cls.user_a.id})

    def test_workspace_visible_to_all(self):
        self.env.invalidate_all()
        found = self.Article.with_user(self.user_b).search([('id', '=', self.ws.id)])
        self.assertEqual(found, self.ws)

    def test_private_invisible_to_other_user(self):
        # Test en RECHERCHE (pas seulement browse) : privé d'autrui absent.
        self.env.invalidate_all()
        found = self.Article.with_user(self.user_b).search(
            [('id', '=', self.priv_a.id)])
        self.assertFalse(found)

    def test_private_visible_to_owner(self):
        self.env.invalidate_all()
        found = self.Article.with_user(self.user_a).search(
            [('id', '=', self.priv_a.id)])
        self.assertEqual(found, self.priv_a)

    def test_manager_sees_all(self):
        self.env.invalidate_all()
        found = self.Article.with_user(self.manager).search(
            [('id', '=', self.priv_a.id)])
        self.assertEqual(found, self.priv_a)

    def test_unlink_other_private_refused(self):
        self.env.invalidate_all()
        # user_b ne voit même pas priv_a → unlink retourne sur recordset vide côté
        # b. On vérifie plutôt qu'il ne peut pas le supprimer via sudo-less browse.
        art_b = self.priv_a.with_user(self.user_b)
        # Le record est hors périmètre : toute écriture/suppression échoue.
        error = False
        try:
            art_b.unlink()
        except Exception:
            error = True
        self.assertTrue(error)
