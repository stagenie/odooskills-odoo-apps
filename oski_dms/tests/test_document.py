import base64
from .common import DmsCommon


class TestDocument(DmsCommon):

    def _make_doc(self, name='CGV.txt', data=b'hello'):
        return self.env['oski.dms.document'].create({
            'name': name,
            'workspace_id': self.ws_root.id,
            'file': base64.b64encode(data),
            'file_name': name,
        })

    def test_create_document_builds_attachment(self):
        doc = self._make_doc()
        self.assertTrue(doc.attachment_id)
        self.assertEqual(base64.b64decode(doc.attachment_id.datas), b'hello')

    def test_related_metadata(self):
        doc = self._make_doc(data=b'abcdef')
        self.assertEqual(doc.file_size, 6)
        self.assertTrue(doc.mimetype)

    def test_owner_default(self):
        doc = self._make_doc()
        self.assertEqual(doc.owner_id, self.env.user)

    def test_default_version_no(self):
        doc = self._make_doc()
        self.assertEqual(doc.version_no, 1)
        self.assertTrue(doc.active)

    def test_workspace_document_count(self):
        self.assertEqual(self.ws_root.document_count, 0)
        doc = self._make_doc()
        self.assertEqual(doc.workspace_id, self.ws_root)
        self.assertEqual(self.ws_root.document_count, 1)

    def test_unlink_removes_attachment(self):
        doc = self._make_doc()
        att_id = doc.attachment_id.id
        self.assertTrue(att_id)
        doc.unlink()
        self.assertFalse(self.env['ir.attachment'].browse(att_id).exists())

    def test_res_name_invalid_model_no_crash(self):
        doc = self._make_doc()
        doc.write({'res_model': 'modele.inexistant', 'res_id': 1})
        self.assertFalse(doc.res_name)
