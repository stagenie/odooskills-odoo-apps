# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
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

    def test_templates_are_offered_by_invoice_type(self):
        """Un modèle « Factures fournisseurs » n'est pas proposé sur une
        facture client, et inversement ; « Toutes » l'est partout."""
        Template = self.env["oski.invoice.comment.template"]
        vendor_only = Template.create({
            "name": "Autoliquidation", "body": "<p>Autoliquidation.</p>",
            "move_types": "in"})
        customer_only = Template.create({
            "name": "Pénalités", "body": "<p>Pénalités de retard.</p>",
            "move_types": "out"})
        bill = self.init_invoice("in_invoice", products=self.product_a)
        self.assertEqual(self.invoice.oski_comment_direction, "out")
        self.assertEqual(bill.oski_comment_direction, "in")
        field = self.env["account.move"]._fields["oski_comment_template_id"]
        self.assertIn("oski_comment_direction", field.domain)
        offered_out = Template.search(
            [("move_types", "in", ("all", self.invoice.oski_comment_direction))])
        offered_in = Template.search(
            [("move_types", "in", ("all", bill.oski_comment_direction))])
        self.assertIn(customer_only, offered_out)
        self.assertNotIn(vendor_only, offered_out)
        self.assertIn(vendor_only, offered_in)
        self.assertNotIn(customer_only, offered_in)
        self.assertIn(self.template_a, offered_out & offered_in)

    def test_a_template_reserved_to_bills_is_refused_on_a_customer_invoice(self):
        vendor_only = self.env["oski.invoice.comment.template"].create({
            "name": "Autoliquidation", "body": "<p>Autoliquidation.</p>",
            "move_types": "in"})
        with self.assertRaises(ValidationError):
            self.invoice.oski_comment_template_id = vendor_only
