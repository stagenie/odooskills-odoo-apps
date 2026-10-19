from odoo.tests.common import TransactionCase


class TestDuplicateGuard(TransactionCase):

    def setUp(self):
        super().setUp()
        self.icp = self.env["ir.config_parameter"].sudo()
        self.icp.set_bool("oski_dup.check_email", True)
        self.icp.set_bool("oski_dup.check_phone", True)
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
        self.icp.set_bool("oski_dup.check_email", False)
        new = self.env["res.partner"].create({"name": "Copie", "email": "dup@test.dz"})
        self.assertFalse(new.oski_duplicate_id)

    def test_underscore_in_email_is_not_a_wildcard(self):
        self.env["res.partner"].create({"name": "Jean", "email": "jean_dupont@test.dz"})
        new = self.env["res.partner"].create({"name": "Autre", "email": "jeanXdupont@test.dz"})
        self.assertFalse(new.oski_duplicate_id, "« _ » ne doit pas jouer le rôle de joker.")
        same = self.env["res.partner"].create({"name": "Copie", "email": "JEAN_DUPONT@test.dz"})
        self.assertTrue(same.oski_duplicate_id)

    def test_settings_can_disable_and_enable_checks(self):
        """Décocher dans les Réglages doit réellement désactiver la détection."""
        settings = self.env["res.config.settings"].create({})
        self.assertTrue(settings.oski_dup_check_email, "Activé par défaut.")
        settings.oski_dup_check_email = False
        settings.execute()
        self.assertFalse(self.env["res.config.settings"].create({}).oski_dup_check_email)
        new = self.env["res.partner"].create({"name": "Copie", "email": "dup@test.dz"})
        self.assertFalse(new.oski_duplicate_id, "Détection email désactivée par les Réglages.")
        settings = self.env["res.config.settings"].create({"oski_dup_check_email": True})
        settings.execute()
        again = self.env["res.partner"].create({"name": "Copie 2", "email": "dup@test.dz"})
        self.assertIn(again.oski_duplicate_id, self.existing | new, "Détection email réactivée.")
        self.assertTrue(again.oski_duplicate_id)

    def test_detection_enabled_when_parameter_unset(self):
        """Sans paramètre (installation neuve), la détection est active."""
        self.icp.search([("key", "like", "oski_dup.check_")]).unlink()
        self.assertTrue(self.env["res.config.settings"].create({}).oski_dup_check_phone)
        new = self.env["res.partner"].create({"name": "Copie", "phone": "+213 5 00"})
        self.assertEqual(new.oski_duplicate_id, self.existing)
