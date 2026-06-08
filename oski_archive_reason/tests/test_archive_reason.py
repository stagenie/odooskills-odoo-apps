from odoo.tests.common import TransactionCase


class TestArchiveReason(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "À archiver"})

    def test_archive_opens_wizard(self):
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
