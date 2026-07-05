import base64
from .common import DmsCommon


class TestAttachExisting(DmsCommon):

    def test_file_existing_attachment_no_copy(self):
        partner = self.env['res.partner'].create({'name': 'ACME'})
        att = self.env['ir.attachment'].create({
            'name': 'contrat.pdf',
            'datas': base64.b64encode(b'PDFDATA'),
            'res_model': 'res.partner', 'res_id': partner.id,
        })
        wizard = self.env['oski.dms.file.wizard'].create({
            'attachment_id': att.id,
            'workspace_id': self.ws_root.id,
        })
        wizard.action_file()
        doc = self.env['oski.dms.document'].search([('attachment_id', '=', att.id)])
        self.assertEqual(len(doc), 1)
        # même octet, pas de duplication
        self.assertEqual(doc.attachment_id, att)
        # rattachement métier repris de l'attachment
        self.assertEqual(doc.res_model, 'res.partner')
        self.assertEqual(doc.res_id, partner.id)

    def test_attachment_count_unchanged(self):
        att = self.env['ir.attachment'].create({
            'name': 'note.txt', 'datas': base64.b64encode(b'N'),
        })
        # `datas` est un champ compute non stocké (search impossible en v19,
        # ValueError "Cannot convert ... to SQL") : on compte le total des
        # ir.attachment plutôt que de filtrer sur ce champ.
        before = self.env['ir.attachment'].search_count([])
        wizard = self.env['oski.dms.file.wizard'].create({
            'attachment_id': att.id, 'workspace_id': self.ws_root.id,
        })
        wizard.action_file()
        after = self.env['ir.attachment'].search_count([])
        self.assertEqual(before, after)  # aucun attachment dupliqué

    def test_unlink_keeps_external_attachment(self):
        """Supprimer un document GED classé depuis une PJ EXTERNE ne doit PAS
        détruire l'attachment source encore utilisé sur l'enregistrement métier.
        """
        partner = self.env['res.partner'].create({'name': 'ACME'})
        att = self.env['ir.attachment'].create({
            'name': 'contrat.pdf',
            'datas': base64.b64encode(b'PDFDATA'),
            'res_model': 'res.partner', 'res_id': partner.id,
        })
        att_id = att.id
        wizard = self.env['oski.dms.file.wizard'].create({
            'attachment_id': att.id,
            'workspace_id': self.ws_root.id,
        })
        wizard.action_file()
        doc = self.env['oski.dms.document'].search([('attachment_id', '=', att.id)])
        doc.unlink()
        # la PJ externe est préservée
        self.assertTrue(self.env['ir.attachment'].browse(att_id).exists())
