"""The internal notification reaches the team, in the company language; the
acknowledgement reaches the requester, in the language of the visit."""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestNotifyMail(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("fr_FR")
        cls.env["ir.module.module"]._load_module_terms(["oski_dev_request"], ["fr_FR"], overwrite=True)
        cls.env["ir.config_parameter"].sudo().set_param("oski_dev_request.notify_email", "team@example.com")
        cls.notify = cls.env.ref("oski_dev_request.mail_template_dev_request_notify")
        cls.ack = cls.env.ref("oski_dev_request.mail_template_dev_request_ack")

    def _request(self, lang):
        return self.env["oski.dev.request"].with_context(lang=lang).create({
            "requester_name": "Awa Diop", "email": "awa@example.com",
            "subject": "Route planning", "description": "Need.",
            "budget_range": "lt_500",
        })

    def _mail(self, template, request):
        mail_id = template.with_context(lang=request.env.lang).send_mail(request.id, force_send=False)
        return self.env["mail.mail"].browse(mail_id)

    def test_notification_goes_to_the_team_not_the_requester(self):
        mail = self._mail(self.notify, self._request("en_US"))
        recipients = (mail.email_to or "") + " ".join(mail.recipient_ids.mapped("email"))
        self.assertIn("team@example.com", recipients)
        self.assertNotIn("awa@example.com", recipients)

    def test_notification_in_company_language_with_labels(self):
        self.env.company.partner_id.lang = "fr_FR"
        mail = self._mail(self.notify, self._request("en_US"))
        self.assertIn("Nouvelle demande de dev", mail.subject)
        self.assertIn("Moins de 500", mail.body_html)
        self.assertNotIn("lt_500", mail.body_html)
        self.env.company.partner_id.lang = "en_US"
        mail = self._mail(self.notify, self._request("fr_FR"))
        self.assertIn("New dev request", mail.subject)
        self.assertIn("Under €500", mail.body_html)

    def test_acknowledgement_follows_the_visit(self):
        self.env.company.partner_id.lang = "en_US"
        mail = self._mail(self.ack, self._request("fr_FR"))
        self.assertIn("Votre demande de développement", mail.subject)
        self.assertIn("awa@example.com", (mail.email_to or "") + " ".join(mail.recipient_ids.mapped("email")))
        mail = self._mail(self.ack, self._request("en_US"))
        self.assertIn("Your development request", mail.subject)
