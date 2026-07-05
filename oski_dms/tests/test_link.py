import base64
from .common import DmsCommon


class TestLink(DmsCommon):

    def test_res_name_computed(self):
        partner = self.env['res.partner'].create({'name': 'Globex'})
        doc = self.env['oski.dms.document'].create({
            'name': 'D', 'workspace_id': self.ws_root.id,
            'file': base64.b64encode(b'z'), 'file_name': 'd.txt',
            'res_model': 'res.partner', 'res_id': partner.id,
        })
        self.assertEqual(doc.res_name, 'Globex')

    def test_open_linked_record(self):
        partner = self.env['res.partner'].create({'name': 'Initech'})
        doc = self.env['oski.dms.document'].create({
            'name': 'D', 'workspace_id': self.ws_root.id,
            'file': base64.b64encode(b'z'), 'file_name': 'd.txt',
            'res_model': 'res.partner', 'res_id': partner.id,
        })
        action = doc.action_open_linked_record()
        self.assertEqual(action['res_model'], 'res.partner')
        self.assertEqual(action['res_id'], partner.id)
