from odoo.tools import BinaryBytes

from odoo.exceptions import ValidationError

from .common import DmsCommon


class TestSettings(DmsCommon):

    def test_max_upload_enforced(self):
        self.env['ir.config_parameter'].sudo().set_int('oski_dms.max_upload_mb', 1)
        big = b'0' * (2 * 1024 * 1024)  # 2 Mo > 1 Mo
        with self.assertRaises(ValidationError):
            self.env['oski.dms.document'].create({
                'name': 'Big', 'workspace_id': self.ws_root.id,
                'file': BinaryBytes(big), 'file_name': 'big.bin',
            })

    def test_default_workspace_applied(self):
        self.env['ir.config_parameter'].sudo().set_int(
            'oski_dms.default_workspace_id', self.ws_root.id)
        default = self.env['oski.dms.document'].default_get(['workspace_id'])
        self.assertEqual(default['workspace_id'], self.ws_root.id)

    def test_under_limit_ok(self):
        self.env['ir.config_parameter'].sudo().set_int('oski_dms.max_upload_mb', 5)
        small = b'0' * 1024
        doc = self.env['oski.dms.document'].create({
            'name': 'Small', 'workspace_id': self.ws_root.id,
            'file': BinaryBytes(small), 'file_name': 'small.bin',
        })
        self.assertTrue(doc.attachment_id)

    def test_settings_display_matches_enforced_limit(self):
        """Paramètre absent = illimité : l'écran doit afficher 0, pas 25."""
        self.env['ir.config_parameter'].sudo().set_str('oski_dms.max_upload_mb', False)
        settings = self.env['res.config.settings'].create({})
        self.assertEqual(settings.dms_max_upload_mb, 0)
        big = b'0' * (30 * 1024 * 1024)  # 30 Mo : accepté quand illimité
        doc = self.env['oski.dms.document'].create({
            'name': 'Gros', 'workspace_id': self.ws_root.id,
            'file': BinaryBytes(big), 'file_name': 'gros.bin',
        })
        self.assertTrue(doc.attachment_id)
