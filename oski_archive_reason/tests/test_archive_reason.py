from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.oski_archive_reason.models.res_partner import ResPartner


class TestArchiveReason(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "À archiver"})

    def test_archive_opens_wizard(self):
        # Simule le bouton « Archiver » du client web.
        with patch.object(ResPartner, "_oski_archive_needs_reason", return_value=True):
            action = self.partner.action_archive()
        self.assertIsInstance(action, dict)
        self.assertEqual(action.get("res_model"), "oski.archive.reason.wizard")
        self.assertTrue(action.get("views"), "L'action doit fournir 'views' (sinon crash client).")
        self.assertTrue(self.partner.active, "Le contact ne doit pas être archivé sans motif.")

    def test_confirmed_archive_sets_inactive_and_logs(self):
        wizard = self.env["oski.archive.reason.wizard"].with_context(
            active_model="res.partner", active_ids=self.partner.ids,
        ).create({"reason": "Doublon"})
        wizard.action_confirm()
        self.assertFalse(self.partner.active, "Le contact doit être archivé après confirmation.")
        bodies = self.partner.message_ids.mapped("body")
        self.assertTrue(
            any("Doublon" in (b or "") for b in bodies),
            "Le motif doit apparaître dans le chatter.",
        )

    def test_direct_confirmed_context_bypasses_wizard(self):
        result = self.partner.with_context(oski_archive_confirmed=True).action_archive()
        self.assertFalse(self.partner.active)
        self.assertNotIsInstance(result, dict)

    def test_server_side_archive_is_immediate(self):
        """Un appel serveur (ex. suppression d'un compte portail) archive tout de suite."""
        result = self.partner.action_archive()
        self.assertFalse(self.partner.active, "Un archivage par le code ne doit pas attendre de motif.")
        self.assertNotIsInstance(result, dict)

    def test_portal_account_deletion_archives_partner(self):
        user = self.env["res.users"].create({
            "name": "Portail à supprimer",
            "login": "oski_archive_portal@example.com",
            "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
        })
        partner = user.partner_id
        user.sudo()._deactivate_portal_user()
        self.assertFalse(partner.active, "Le contact du compte portail supprimé doit être archivé.")

    def test_wizard_without_records_raises(self):
        from odoo.exceptions import UserError
        wizard = self.env["oski.archive.reason.wizard"].create({"reason": "Rien"})
        with self.assertRaises(UserError):
            wizard.action_confirm()
