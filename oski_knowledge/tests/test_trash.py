from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestTrash(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Article = cls.env['knowledge.article']
        cls.root = cls.Article.create({'name': 'R', 'section': 'workspace'})
        cls.child = cls.Article.create({'name': 'C', 'parent_id': cls.root.id})

    def test_archive_whole_subtree(self):
        self.root.action_archive_to_trash()
        self.assertFalse(self.root.active)
        self.assertFalse(self.child.active)

    def test_restore_reactivates(self):
        self.root.action_archive_to_trash()
        self.child.action_restore()
        self.assertTrue(self.child.active)

    def test_restore_reanchors_when_parent_archived(self):
        # Restaurer un enfant dont le parent reste archivé le ré-ancre en racine.
        self.root.action_archive_to_trash()
        self.child.action_restore()
        self.assertTrue(self.child.active)
        self.assertFalse(self.child.parent_id)
        self.assertEqual(self.child.root_article_id, self.child)
