from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestKnowledgeArticle(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Article = cls.env['knowledge.article']
        cls.root = cls.Article.create({'name': 'Racine', 'section': 'workspace'})
        cls.child = cls.Article.create({'name': 'Enfant', 'parent_id': cls.root.id})
        cls.grandchild = cls.Article.create({'name': 'Petit-enfant', 'parent_id': cls.child.id})

    def test_parent_path_and_root(self):
        self.assertEqual(self.grandchild.root_article_id, self.root)
        self.assertEqual(self.root.root_article_id, self.root)
        self.assertTrue(self.grandchild.parent_path.startswith(f'{self.root.id}/'))

    def test_section_inherited_from_root(self):
        # section n'est éditable que sur la racine : les descendants la recopient.
        self.assertEqual(self.child.section, 'workspace')
        self.assertEqual(self.grandchild.section, 'workspace')
        self.root.section = 'private'
        self.assertEqual(self.child.section, 'private')
        self.assertEqual(self.grandchild.section, 'private')

    def test_section_recompute_on_subtree_move(self):
        # Déplacer un sous-arbre sous une racine private recalcule toute la descendance.
        priv_root = self.Article.create({'name': 'Privé', 'section': 'private'})
        self.child.parent_id = priv_root.id
        self.assertEqual(self.child.section, 'private')
        self.assertEqual(self.grandchild.section, 'private')
        self.assertEqual(self.grandchild.root_article_id, priv_root)

    def test_body_text_extraction(self):
        art = self.Article.create({
            'name': 'Doc', 'body': '<h1>Titre</h1><p>Bonjour <b>monde</b></p>'})
        self.assertIn('Titre', art.body_text)
        self.assertIn('Bonjour', art.body_text)
        self.assertNotIn('<h1>', art.body_text)

    def test_body_text_empty_when_body_empty(self):
        art = self.Article.create({'name': 'Vide'})
        self.assertFalse(art.body_text)

    def test_cycle_forbidden(self):
        with self.assertRaises(ValidationError):
            self.root.parent_id = self.grandchild.id

    def test_private_requires_owner(self):
        # section private sans owner_id interdit.
        art = self.Article.create({'name': 'P', 'section': 'private'})
        with self.assertRaises(ValidationError):
            art.owner_id = False

    def test_cycle_forbidden_batch_write(self):
        # Batch write : un seul enregistrement en cycle doit bloquer TOUT le batch
        # (ValidationError levée avant super().write(), donc B reste intact = parent_id=False).
        root_a = self.Article.create({'name': 'RacineA'})
        child_a = self.Article.create({'name': 'EnfantA', 'parent_id': root_a.id})
        root_b = self.Article.create({'name': 'RacineB'})
        self.Article.create({'name': 'EnfantB', 'parent_id': root_b.id})
        try:
            (root_a + root_b).write({'parent_id': child_a.id})
            self.fail("ValidationError attendue pour le cycle sur root_a")
        except ValidationError:
            pass
        self.assertFalse(root_b.parent_id)

    def test_child_count(self):
        self.assertEqual(self.root.child_count, 1)
        self.assertEqual(self.child.child_count, 1)
        self.assertEqual(self.grandchild.child_count, 0)
