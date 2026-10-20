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
        cls.user_a.groups_id = [(4, cls.grp_a.id)]
        cls.user_b = cls._make_user('dms_b', ['oski_dms.group_dms_user'])
        cls.user_b.groups_id = [(4, cls.grp_b.id)]
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

    def test_cannot_move_document_to_workspace_without_write(self):
        """Déplacer un document vers un espace où l'on n'écrit pas est refusé
        (le contrôle standard de `write` ne porte que sur l'espace d'origine)."""
        ws_b = self.Workspace.create({
            'name': 'Espace B',
            'read_group_ids': [(4, self.grp_b.id)],
            'write_group_ids': [(4, self.grp_b.id)],
        })
        with self.assertRaises(AccessError):
            self.doc_a.with_user(self.user_a).write({'workspace_id': ws_b.id})
        self.assertEqual(self.doc_a.workspace_id, self.ws_a)

    def test_move_document_between_writable_workspaces(self):
        ws_a2 = self.Workspace.create({
            'name': 'Espace A2',
            'read_group_ids': [(4, self.grp_a.id)],
            'write_group_ids': [(4, self.grp_a.id)],
        })
        self.doc_a.with_user(self.user_a).write({'workspace_id': ws_a2.id})
        self.assertEqual(self.doc_a.workspace_id, ws_a2)

    def test_writer_or_manager_group_reads_documents(self):
        """Un membre des groupes écriture / gestion voit l'espace (règle
        espace) : il doit aussi en lire les documents."""
        ws_w = self.Workspace.create({
            'name': 'Écriture seule', 'write_group_ids': [(4, self.grp_b.id)],
        })
        doc = self.env['oski.dms.document'].create({
            'name': 'W', 'workspace_id': ws_w.id,
            'file': base64.b64encode(b'w'), 'file_name': 'w.txt',
        })
        self.assertEqual(doc.with_user(self.user_b).read(['name'])[0]['name'], 'W')
        doc.with_user(self.user_b).write({'name': 'W2'})

    def test_attachment_not_readable_by_non_member(self):
        """La pièce jointe (et donc /web/content) suit le droit du document."""
        att = self.doc_a.attachment_id
        with self.assertRaises(AccessError):
            att.with_user(self.user_b).read(['datas'])
        self.assertTrue(att.with_user(self.user_a).read(['datas'])[0]['datas'])

    def test_read_group_and_count_do_not_leak(self):
        Doc = self.env['oski.dms.document'].with_user(self.user_b)
        groups = Doc._read_group([], groupby=['workspace_id'], aggregates=['__count'])
        self.assertNotIn(self.ws_a, [ws for ws, _c in groups])
        self.assertEqual(Doc.search_count([('name', 'ilike', 'Secret')]), 0)


@tagged('post_install', '-at_install')
class TestMultiCompany(DmsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env['res.company'].create({'name': 'Société B GED'})
        cls.grp = cls.env['res.groups'].create({'name': 'Équipe MC'})
        cls.user = cls._make_user('dms_mc', ['oski_dms.group_dms_manager'])
        cls.user.groups_id = [(4, cls.grp.id)]
        cls.ws_b = cls.Workspace.create({
            'name': 'Espace société B', 'company_id': cls.company_b.id,
            'read_group_ids': [(4, cls.grp.id)],
        })
        cls.doc_b = cls.env['oski.dms.document'].create({
            'name': 'Doc société B', 'workspace_id': cls.ws_b.id,
            'file': base64.b64encode(b'b'), 'file_name': 'b.txt',
        })

    def test_other_company_hidden_even_for_manager(self):
        Doc = self.env['oski.dms.document'].with_user(self.user)
        self.assertNotIn(self.doc_b, Doc.search([]))
        self.assertNotIn(self.ws_b, self.Workspace.with_user(self.user).search([]))

    def test_visible_once_company_allowed(self):
        self.user.company_ids = [(4, self.company_b.id)]
        Doc = self.env['oski.dms.document'].with_user(self.user).with_context(
            allowed_company_ids=[self.env.company.id, self.company_b.id])
        self.assertIn(self.doc_b, Doc.search([]))

    def test_parent_workspace_same_company(self):
        from odoo.exceptions import UserError
        with self.assertRaises(UserError):
            self.Workspace.create({
                'name': 'Enfant incohérent', 'parent_id': self.ws_root.id,
                'company_id': self.company_b.id,
            })
