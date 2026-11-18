"""La notification part à l'équipe (jamais au demandeur) ; l'accusé part
au demandeur, dans sa langue."""
from lxml import etree

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from .common import feedback_vals, make_store_data


@tagged("post_install", "-at_install")
class TestNotifyMail(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_store_data(cls)
        cls.env["ir.config_parameter"].sudo().set_param(
            "oski_module_feedback.notify_email", "info@odooskills.com")
        cls.new_tpl = cls.env.ref("oski_module_feedback.mail_template_feedback_new")
        cls.ack_tpl = cls.env.ref("oski_module_feedback.mail_template_feedback_ack")

    def _mails(self, rec):
        return self.env["mail.mail"].search([("res_id", "=", rec.id), ("model", "=", rec._name)])

    def _recipients(self, mail):
        return (mail.email_to or "") + " " + " ".join(mail.recipient_ids.mapped("email"))

    def test_new_goes_to_notify_email(self):
        rec = self.env["oski.module.feedback"].create(feedback_vals(self))
        rec._send_new_notifications()
        team = self._mails(rec).filtered(lambda m: "info@odooskills.com" in self._recipients(m))
        self.assertEqual(len(team), 1)
        self.assertNotIn("awa@example.com", self._recipients(team))
        self.assertIn("awa@example.com", team.reply_to or "")

    def test_ack_goes_to_requester(self):
        rec = self.env["oski.module.feedback"].create(feedback_vals(self))
        rec._send_new_notifications()
        ack = self._mails(rec).filtered(lambda m: "awa@example.com" in self._recipients(m))
        self.assertEqual(len(ack), 1)
        self.assertIn(rec.name, ack.subject)

    def test_notify_param_override(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "oski_module_feedback.notify_email", "ops@example.com")
        rec = self.env["oski.module.feedback"].create(feedback_vals(self))
        rec._send_new_notifications()
        self.assertTrue(self._mails(rec).filtered(lambda m: "ops@example.com" in self._recipients(m)))

    def test_ack_lang_is_partner_lang(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        self.portal_user.partner_id.lang = "fr_FR"
        rec = self.env["oski.module.feedback"].create(feedback_vals(self))
        self.assertEqual(self.ack_tpl._render_lang(rec.ids)[rec.id], "fr_FR")

    def test_template_no_default_to(self):
        self.assertFalse(self.new_tpl.use_default_to)
        self.assertFalse(self.ack_tpl.use_default_to)

    def test_filters_exist(self):
        arch = self.env["oski.module.feedback"].get_view(view_type="search")["arch"]
        names = etree.fromstring(arch).xpath("//filter/@name")
        for name in ("filter_bug", "filter_change", "filter_improvement", "filter_packs", "filter_from_trial"):
            self.assertIn(name, names)

    def test_module_smart_button(self):
        arch = self.env["oski.module"].get_view(view_type="form")["arch"]
        self.assertIn("action_view_feedback", arch)
        action = self.paid.action_view_feedback()
        self.assertEqual(action["domain"], [("module_id", "=", self.paid.id)])
