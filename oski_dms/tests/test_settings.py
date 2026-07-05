import base64

from odoo.exceptions import ValidationError

from .common import DmsCommon


class TestSettings(DmsCommon):

    def test_max_upload_enforced(self):
        self.env['ir.config_parameter'].sudo().set_param('oski_dms.max_upload_mb', '1')
        big = b'0' * (2 * 1024 * 1024)  # 2 Mo > 1 Mo
        with self.assertRaises(ValidationError):
            self.env['oski.dms.document'].create({
                'name': 'Big', 'workspace_id': self.ws_root.id,
                'file': base64.b64encode(big), 'file_name': 'big.bin',
            })

    def test_default_workspace_applied(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'oski_dms.default_workspace_id', str(self.ws_root.id))
        default = self.env['oski.dms.document'].default_get(['workspace_id'])
        self.assertEqual(default['workspace_id'], self.ws_root.id)

    def test_under_limit_ok(self):
        self.env['ir.config_parameter'].sudo().set_param('oski_dms.max_upload_mb', '5')
        small = b'0' * 1024
        doc = self.env['oski.dms.document'].create({
            'name': 'Small', 'workspace_id': self.ws_root.id,
            'file': base64.b64encode(small), 'file_name': 'small.bin',
        })
        self.assertTrue(doc.attachment_id)
