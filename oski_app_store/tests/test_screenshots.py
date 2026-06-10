import base64

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestScreenshots(TransactionCase):
    def test_screenshot_ids_field(self):
        module = self.env["oski.module"].create(
            {"name": "Test Shots", "technical_name": "oski_test_shots"}
        )
        att = self.env["ir.attachment"].create(
            {
                "name": "screenshot_01.png",
                "datas": base64.b64encode(b"fakepng"),
                "public": True,
            }
        )
        module.screenshot_ids = [(6, 0, [att.id])]
        self.assertEqual(len(module.screenshot_ids), 1)
        self.assertTrue(module.screenshot_ids.public)
