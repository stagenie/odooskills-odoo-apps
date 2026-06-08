import base64

from odoo.tests.common import TransactionCase


class TestQrVcard(TransactionCase):

    def test_qr_generated_with_name(self):
        partner = self.env["res.partner"].create({"name": "Acme SARL"})
        self.assertTrue(
            partner.oski_qr_vcard,
            "Le QR doit être généré dès qu'un contact a un nom.",
        )

    def test_qr_is_valid_png(self):
        partner = self.env["res.partner"].create({"name": "Acme SARL"})
        raw = base64.b64decode(partner.oski_qr_vcard)
        self.assertEqual(
            raw[:8], b"\x89PNG\r\n\x1a\n",
            "Le binaire produit doit être un PNG valide.",
        )

    def test_vcard_content(self):
        partner = self.env["res.partner"].create({
            "name": "Jean Test",
            "email": "jean@test.dz",
            "phone": "+213 555 00 00 00",
            "function": "Directeur",
        })
        vcard = partner._oski_build_vcard()
        self.assertIn("BEGIN:VCARD", vcard)
        self.assertIn("VERSION:3.0", vcard)
        self.assertIn("FN:Jean Test", vcard)
        self.assertIn("EMAIL;TYPE=INTERNET:jean@test.dz", vcard)
        self.assertIn("TEL;TYPE=WORK,VOICE:+213 555 00 00 00", vcard)
        self.assertIn("TITLE:Directeur", vcard)
        self.assertIn("END:VCARD", vcard)
