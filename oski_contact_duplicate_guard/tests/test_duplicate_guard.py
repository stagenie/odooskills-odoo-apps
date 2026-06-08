from odoo.tests.common import TransactionCase


class TestDuplicateGuard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.icp = self.env["ir.config_parameter"].sudo()
        self.icp.set_param("oski_dup.check_email", "True")
        self.icp.set_param("oski_dup.check_phone", "True")
        self.existing = self.env["res.partner"].create({
            "name": "Original", "email": "dup@test.dz", "phone": "+213 5 00",
        })

    def test_create_email_duplicate_is_linked(self):
        new = self.env["res.partner"].create({"name": "Copie", "email": "DUP@test.dz"})
        self.assertEqual(new.oski_duplicate_id, self.existing,
                         "Le doublon email doit être détecté (insensible à la casse).")

    def test_create_phone_duplicate_is_linked(self):
        new = self.env["res.partner"].create({"name": "Copie", "phone": "+213 5 00"})
        self.assertEqual(new.oski_duplicate_id, self.existing)

    def test_no_duplicate_when_unique(self):
        new = self.env["res.partner"].create({"name": "Unique", "email": "fresh@test.dz"})
        self.assertFalse(new.oski_duplicate_id)

    def test_onchange_email_returns_warning(self):
        partner = self.env["res.partner"].new({"email": "dup@test.dz"})
        result = partner._onchange_oski_email_duplicate()
        self.assertTrue(result and "warning" in result)
        self.assertEqual(partner.oski_duplicate_id, self.existing)

    def test_disabled_check_skips_detection(self):
        self.icp.set_param("oski_dup.check_email", "False")
        new = self.env["res.partner"].create({"name": "Copie", "email": "dup@test.dz"})
        self.assertFalse(new.oski_duplicate_id)
