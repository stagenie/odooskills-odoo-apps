# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestInvoiceCommentTemplate(AccountTestInvoicingCommon):
    """Tests des modèles de remarques réutilisables sur factures."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template_a = cls.env["oski.invoice.comment.template"].create({
            "name": "Mentions légales",
            "body": "<p>Merci de régler sous 30 jours.</p>",
        })
        cls.template_b = cls.env["oski.invoice.comment.template"].create({
            "name": "Escompte",
            "body": "<p>Escompte de 2% pour paiement comptant.</p>",
        })
        cls.invoice = cls.init_invoice(
            "out_invoice", products=cls.product_a,
        )

    def test_apply_template_fills_narration(self):
        """Appliquer un template remplit narration avec le body."""
        self.invoice.oski_comment_template_id = self.template_a
        self.invoice.action_oski_apply_comment_template()
        self.assertIn("Merci de régler sous 30 jours", self.invoice.narration)

    def test_change_template_updates_narration(self):
        """Changer de template met à jour narration."""
        self.invoice.oski_comment_template_id = self.template_a
        self.invoice.action_oski_apply_comment_template()
        self.assertIn("Merci de régler sous 30 jours", self.invoice.narration)
        self.invoice.oski_comment_template_id = self.template_b
        self.invoice.action_oski_apply_comment_template()
        self.assertIn("Escompte de 2%", self.invoice.narration)
        self.assertNotIn("Merci de régler sous 30 jours", self.invoice.narration)

    def test_remove_template_keeps_narration(self):
        """Retirer le template conserve la narration existante."""
        self.invoice.oski_comment_template_id = self.template_a
        self.invoice.action_oski_apply_comment_template()
        self.assertIn("Merci de régler sous 30 jours", self.invoice.narration)
        self.invoice.oski_comment_template_id = False
        self.invoice.action_oski_apply_comment_template()
        self.assertIn("Merci de régler sous 30 jours", self.invoice.narration)
