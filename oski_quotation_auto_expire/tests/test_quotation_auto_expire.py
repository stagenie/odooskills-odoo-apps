from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestQuotationAutoExpire(TransactionCase):
    """La tâche planifiée s'appelle directement : ce qui est éprouvé, c'est
    la règle, pas l'ordonnanceur d'Odoo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({
            "oski_quote_expire_active": True,
            "oski_quote_reminder_days": 3,
        })
        cls.customer = cls.env["res.partner"].create({"name": "Client Essai"})
        cls.product = cls.env["product.product"].create({
            "name": "Article Essai", "list_price": 100.0, "type": "consu"})
        cls.today = fields.Date.context_today(cls.env["sale.order"])
        cls.salesperson = cls.env["res.users"].create({
            "name": "Vendeuse", "login": "oski_expire_vendeuse",
            "group_ids": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("sales_team.group_sale_salesman").id])]})

    def _order(self, validity, state="draft", **values):
        order = self.env["sale.order"].create(dict({
            "partner_id": self.customer.id,
            "user_id": self.salesperson.id,
            "validity_date": validity,
            "order_line": [(0, 0, {
                "product_id": self.product.id, "product_uom_qty": 1})],
        }, **values))
        if state == "sent":
            order.action_quotation_sent()
        elif state == "sale":
            order.action_confirm()
        return order

    def _run(self):
        return self.env["sale.order"]._oski_cron_expire_quotations()

    def _activities(self, order):
        return self.env["mail.activity"].search([
            ("res_model", "=", "sale.order"), ("res_id", "=", order.id)])

    # -- Péremption -------------------------------------------------------

    def test_an_expired_quotation_is_cancelled(self):
        order = self._order(self.today - timedelta(days=1))
        self._run()
        self.assertEqual(order.state, "cancel")
        self.assertEqual(order.oski_expired_on, self.today)

    def test_the_cancellation_says_why_on_the_record(self):
        order = self._order(self.today - timedelta(days=1))
        known = order.message_ids
        self._run()
        posted = order.message_ids - known
        self.assertTrue(posted, "l'annulation nocturne doit laisser une trace")
        self.assertTrue(
            any("périmé" in message.body.lower() for message in posted),
            "la trace doit dire POURQUOI le devis a été annulé")

    def test_a_quotation_still_valid_is_left_alone(self):
        order = self._order(self.today + timedelta(days=10))
        self._run()
        self.assertEqual(order.state, "draft")
        self.assertFalse(order.oski_expired_on)

    def test_a_quotation_expiring_today_is_left_alone(self):
        """Le jour de l'échéance, le devis vaut encore."""
        order = self._order(self.today)
        self._run()
        self.assertEqual(order.state, "draft")

    def test_a_sent_quotation_expires_too(self):
        order = self._order(self.today - timedelta(days=1), state="sent")
        self._run()
        self.assertEqual(order.state, "cancel")

    def test_a_confirmed_order_is_never_touched(self):
        order = self._order(self.today - timedelta(days=1), state="sale")
        self._run()
        self.assertEqual(order.state, "sale")
        self.assertFalse(order.oski_expired_on)

    def test_a_locked_quotation_is_never_touched(self):
        order = self._order(self.today - timedelta(days=1))
        order.locked = True
        self._run()
        self.assertNotEqual(order.state, "cancel")

    def test_a_quotation_without_validity_date_never_expires(self):
        order = self._order(False)
        self._run()
        self.assertEqual(order.state, "draft")

    def test_nothing_expires_when_the_company_says_no(self):
        self.company.oski_quote_expire_active = False
        order = self._order(self.today - timedelta(days=1))
        self._run()
        self.assertEqual(order.state, "draft")

    # -- Relance ----------------------------------------------------------

    def test_the_salesperson_is_reminded_before_the_deadline(self):
        order = self._order(self.today + timedelta(days=2))
        self._run()
        activity = self._activities(order)
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity.user_id, self.salesperson)
        self.assertEqual(activity.date_deadline, order.validity_date)
        self.assertEqual(order.oski_reminder_sent_on, self.today)

    def test_the_reminder_is_an_activity_and_not_an_email(self):
        """Le vendeur vit dans Odoo ; un courriel de plus s'y perd.

        Le compteur se prend APRÈS la création du devis : celle-ci notifie
        déjà ses abonnés, et confondre les deux ferait passer un courriel
        d'Odoo pour un courriel du module.
        """
        order = self._order(self.today + timedelta(days=2))
        before = self.env["mail.mail"].search_count([])
        self._run()
        self.assertTrue(self._activities(order))
        self.assertEqual(self.env["mail.mail"].search_count([]), before)

    def test_a_far_away_deadline_raises_no_reminder(self):
        order = self._order(self.today + timedelta(days=30))
        self._run()
        self.assertFalse(self._activities(order))

    def test_the_reminder_is_sent_once_a_day(self):
        order = self._order(self.today + timedelta(days=2))
        self._run()
        self._run()
        self.assertEqual(len(self._activities(order)), 1)

    def test_no_reminder_when_the_delay_is_zero(self):
        self.company.oski_quote_reminder_days = 0
        order = self._order(self.today + timedelta(days=2))
        self._run()
        self.assertFalse(self._activities(order))

    def test_the_reminder_lives_without_the_expiry(self):
        """Les deux réglages sont indépendants : on peut vouloir être prévenu
        sans laisser Odoo annuler quoi que ce soit."""
        self.company.oski_quote_expire_active = False
        order = self._order(self.today + timedelta(days=2))
        stale = self._order(self.today - timedelta(days=1))
        self._run()
        self.assertTrue(self._activities(order))
        self.assertEqual(stale.state, "draft")

    def test_a_quotation_expiring_today_is_reminded_then_expires_tomorrow(self):
        """L'ordre compte : relance d'abord, péremption ensuite."""
        order = self._order(self.today)
        self._run()
        self.assertTrue(self._activities(order))
        self.assertEqual(order.state, "draft")
