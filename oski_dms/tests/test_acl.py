import base64
from odoo.exceptions import AccessError
from odoo.tests import tagged
from .common import DmsCommon


@tagged('post_install', '-at_install')
class TestAcl(DmsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.grp_a = cls.env['res.groups'].create({'name': 'Équipe A'})
        cls.grp_b = cls.env['res.groups'].create({'name': 'Équipe B'})
        cls.user_a = cls._make_user('dms_a', ['oski_dms.group_dms_user'])
        cls.user_a.group_ids = [(4, cls.grp_a.id)]
        cls.user_b = cls._make_user('dms_b', ['oski_dms.group_dms_user'])
        cls.user_b.group_ids = [(4, cls.grp_b.id)]
        cls.mgr = cls._make_user('dms_mgr', ['oski_dms.group_dms_manager'])
        cls.ws_a = cls.Workspace.create({
            'name': 'Espace A',
            'read_group_ids': [(4, cls.grp_a.id)],
            'write_group_ids': [(4, cls.grp_a.id)],
            'manage_group_ids': [(4, cls.grp_a.id)],
        })
        cls.doc_a = cls.env['oski.dms.document'].create({
            'name': 'Secret A', 'workspace_id': cls.ws_a.id,
            'file': base64.b64encode(b'x'), 'file_name': 'a.txt',
        })

    def test_member_reads(self):
        doc = self.doc_a.with_user(self.user_a)
        self.assertEqual(doc.name, 'Secret A')

    def test_non_member_cannot_read(self):
        # user_b (Équipe B) ne doit PAS voir un doc de l'Espace A
        docs = self.env['oski.dms.document'].with_user(self.user_b).search([])
        self.assertNotIn(self.doc_a.id, docs.ids)

    def test_non_member_access_error_on_direct_read(self):
        with self.assertRaises(AccessError):
            self.doc_a.with_user(self.user_b).read(['name'])

    def test_manager_sees_all(self):
        docs = self.env['oski.dms.document'].with_user(self.mgr).search([])
        self.assertIn(self.doc_a.id, docs.ids)

    def test_no_write_without_write_group(self):
        ws_ro = self.Workspace.create({
            'name': 'Lecture seule', 'read_group_ids': [(4, self.grp_b.id)],
        })
        doc = self.env['oski.dms.document'].create({
            'name': 'RO', 'workspace_id': ws_ro.id,
            'file': base64.b64encode(b'y'), 'file_name': 'ro.txt',
        })
        with self.assertRaises(AccessError):
            doc.with_user(self.user_b).write({'name': 'hack'})
