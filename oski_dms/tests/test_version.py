import base64
from .common import DmsCommon


class TestVersion(DmsCommon):

    def _doc(self):
        return self.env['oski.dms.document'].create({
            'name': 'Doc', 'workspace_id': self.ws_root.id,
            'file': base64.b64encode(b'v1'), 'file_name': 'Doc.txt',
        })

    def test_new_version(self):
        doc = self._doc()
        new = doc.action_new_version(base64.b64encode(b'v2'), 'Doc.txt')
        self.assertEqual(new.version_no, 2)
        self.assertEqual(new.previous_version_id, doc)
        self.assertFalse(doc.active)
        self.assertTrue(new.active)
        self.assertEqual(base64.b64decode(new.attachment_id.datas), b'v2')

    def test_new_version_keeps_metadata(self):
        doc = self._doc()
        doc.tag_ids = [(0, 0, {'name': 'Ref'})]
        new = doc.action_new_version(base64.b64encode(b'v2'), 'Doc.txt')
        self.assertEqual(new.workspace_id, doc.workspace_id)
        self.assertEqual(new.tag_ids.mapped('name'), ['Ref'])

    def test_restore_version(self):
        doc = self._doc()
        new = doc.action_new_version(base64.b64encode(b'v2'), 'Doc.txt')
        restored = doc.action_restore_version()
        self.assertTrue(doc.active)
        self.assertFalse(new.active)
        self.assertEqual(restored, doc)
