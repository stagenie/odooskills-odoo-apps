from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMailQueueMonitor(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Check = cls.env["oski.mail.queue.check"]
        cls.Mail = cls.env["mail.mail"]
        # La file d'une base réelle n'est jamais vide : on part d'une file
        # connue, sinon les comptes mesurés dépendraient de l'historique.
        cls.Mail.search([]).unlink()

    def _mail(self, state, failure_type=None, age_hours=0):
        mail = self.Mail.create({
            "subject": "Essai",
            "email_to": "destinataire@example.com",
            "body_html": "<p>corps</p>",
            "state": state,
            "failure_type": failure_type or False,
        })
        if age_hours:
            born = fields.Datetime.now() - timedelta(hours=age_hours)
            self.env.cr.execute(
                "UPDATE mail_mail SET create_date = %s WHERE id = %s", (born, mail.id))
            mail.invalidate_recordset(["create_date"])
        return mail

    def test_measure_counts_pending_and_failed(self):
        self._mail("outgoing")
        self._mail("outgoing", age_hours=10)
        self._mail("exception", failure_type="mail_smtp")
        self._mail("sent")
        measure = self.Check._measure_queue()
        self.assertEqual(measure["pending_count"], 2)
        self.assertEqual(measure["failed_count"], 1)
        self.assertGreater(measure["oldest_pending_hours"], 9.0)

    def test_verdict_ok_on_a_healthy_queue(self):
        self._mail("outgoing")
        self.assertEqual(self.Check._verdict_for(self.Check._measure_queue()), "ok")

    def test_a_single_failure_is_enough_to_alert(self):
        self._mail("exception", failure_type="mail_smtp")
        self.assertEqual(self.Check._verdict_for(self.Check._measure_queue()), "critical")

    def test_a_queue_at_a_standstill_is_a_warning(self):
        self._mail("outgoing", age_hours=48)
        self.assertEqual(self.Check._verdict_for(self.Check._measure_queue()), "warning")

    def test_the_standstill_threshold_is_a_parameter(self):
        self._mail("outgoing", age_hours=48)
        self.env["ir.config_parameter"].sudo().set_param(
            "oski_mail_queue_monitor.max_pending_hours", "72")
        self.assertEqual(self.Check._verdict_for(self.Check._measure_queue()), "ok")

    def test_note_names_the_causes(self):
        self._mail("exception", failure_type="mail_smtp")
        self._mail("exception", failure_type="mail_smtp")
        self._mail("exception", failure_type="mail_email_invalid")
        note = self.Check._note_for(self.Check._measure_queue())
        self.assertIn("2", note)
        self.assertIn("Connection failed", note)
        self.assertIn("Invalid email address", note)

    def test_cron_records_and_alerts(self):
        self._mail("exception", failure_type="mail_smtp")
        check = self.Check._cron_check_queue()
        self.assertEqual(check.verdict, "critical")
        self.assertEqual(check.failed_count, 1)
        self.assertTrue(check._open_alerts())

    def test_a_lasting_failure_raises_a_single_alert(self):
        """Une panne qui dure des semaines ne doit pas produire une activité
        par jour : c'est ainsi qu'une alerte cesse d'être lue."""
        self._mail("exception", failure_type="mail_smtp")
        first = self.Check._cron_check_queue()
        opened = first._open_alerts()
        second = self.Check._cron_check_queue()
        self.assertEqual(second.verdict, "critical")
        self.assertEqual(second._open_alerts(), opened)

    def test_a_healthy_queue_raises_nothing(self):
        self._mail("outgoing")
        check = self.Check._cron_check_queue()
        self.assertEqual(check.verdict, "ok")
        self.assertFalse(check._open_alerts())

    def test_a_new_degradation_alerts_again_once_closed(self):
        self._mail("exception", failure_type="mail_smtp")
        first = self.Check._cron_check_queue()
        first._open_alerts().unlink()
        second = self.Check._cron_check_queue()
        self.assertTrue(second._open_alerts())

    def test_retry_puts_failures_back_in_the_queue(self):
        failed = self._mail("exception", failure_type="mail_smtp")
        sent = self._mail("sent")
        check = self.Check._cron_check_queue()
        check.action_retry_failed_mails()
        self.assertEqual(failed.state, "outgoing")
        self.assertEqual(sent.state, "sent")

    def test_the_journal_is_closed_to_ordinary_users(self):
        """``TransactionCase.env`` est superutilisateur : sans ``with_user``,
        aucun droit n'est éprouvé."""
        user = self.env["res.users"].create({
            "name": "Employé", "login": "oski_mail_employe",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])]})
        self.Check._cron_check_queue()
        with self.assertRaises(AccessError):
            self.Check.with_user(user).search([])[:1].read(["verdict"])

    def test_the_alert_sends_no_mail(self):
        """La promesse du module : l'alerte ne passe pas par la file qu'elle
        surveille. Odoo notifie l'assigné d'une activité par courriel ; ce
        module coupe cette notification, et ce test le vérifie."""
        self._mail("exception", failure_type="mail_smtp")
        before = self.Mail.search_count([])
        check = self.Check._cron_check_queue()
        self.assertTrue(check._open_alerts())
        self.assertEqual(self.Mail.search_count([]), before)
