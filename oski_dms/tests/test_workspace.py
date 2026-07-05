from .common import DmsCommon


class TestWorkspace(DmsCommon):

    def test_complete_name(self):
        self.assertEqual(self.ws_child.complete_name, 'Général / Contrats')

    def test_parent_tree(self):
        self.assertEqual(self.ws_child.parent_id, self.ws_root)
        self.assertIn(self.ws_child, self.ws_root.child_ids)

    def test_document_count_zero(self):
        self.assertEqual(self.ws_root.document_count, 0)
