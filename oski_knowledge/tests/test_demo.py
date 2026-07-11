from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestKnowledgeDemo(TransactionCase):
    def test_demo_tree_loaded(self):
        # Les enregistrements démo existent et forment un arbre cohérent.
        root = self.env.ref('oski_knowledge.demo_root', raise_if_not_found=False)
        if not root:
            self.skipTest("Démo non chargée (base sans --with-demo)")
        self.assertEqual(root.section, 'workspace')
        faq = self.env.ref('oski_knowledge.demo_faq')
        self.assertEqual(faq.parent_id, root)
        self.assertEqual(faq.section, 'workspace')
        self.assertTrue(faq.body_text)
