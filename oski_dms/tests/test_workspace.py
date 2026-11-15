from .common import DmsCommon


class TestWorkspace(DmsCommon):

    def test_complete_name(self):
        self.assertEqual(self.ws_child.complete_name, 'Général / Contrats')

    def test_the_delivered_workspace_speaks_the_admin_language(self):
        """L'espace livré est renommé à l'installation dans la langue de
        l'administrateur (``name`` n'est pas traduisible)."""
        from odoo.addons.oski_dms import _oski_dms_post_init
        workspace = self.env.ref("oski_dms.dms_workspace_general")
        self.env["res.lang"]._activate_lang("fr_FR")
        admin = self.env.ref("base.user_admin")
        admin.lang = "fr_FR"
        _oski_dms_post_init(self.env)
        self.assertEqual(workspace.name, "Général")
        admin.lang = "en_US"
        _oski_dms_post_init(self.env)
        self.assertEqual(workspace.name, "General")

    def test_parent_tree(self):
        self.assertEqual(self.ws_child.parent_id, self.ws_root)
        self.assertIn(self.ws_child, self.ws_root.child_ids)

    def test_document_count_zero(self):
        self.assertEqual(self.ws_root.document_count, 0)
