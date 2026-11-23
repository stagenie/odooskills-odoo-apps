from odoo.tools import BinaryBytes
from .common import DmsCommon


class TestDocument(DmsCommon):

    def _make_doc(self, name='CGV.txt', data=b'hello'):
        return self.env['oski.dms.document'].create({
            'name': name,
            'workspace_id': self.ws_root.id,
            'file': BinaryBytes(data),
            'file_name': name,
        })

    def test_create_document_builds_attachment(self):
        doc = self._make_doc()
        self.assertTrue(doc.attachment_id)
        self.assertEqual(doc.attachment_id.raw.content, b'hello')

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

    def test_preview_kind(self):
        """Un PDF et une image ont un aperçu ; un texte reste à télécharger."""
        pdf = self._make_doc(name='plan.pdf', data=b'%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF')
        self.assertTrue(pdf.is_pdf)
        self.assertFalse(pdf.is_image)
        png = self._make_doc(name='logo.png', data=(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'))
        self.assertTrue(png.is_image)
        txt = self._make_doc()
        self.assertFalse(txt.is_pdf or txt.is_image)

    def test_form_shows_a_preview(self):
        arch = self.env.ref('oski_dms.view_dms_document_form').arch
        self.assertIn('pdf_viewer', arch)
