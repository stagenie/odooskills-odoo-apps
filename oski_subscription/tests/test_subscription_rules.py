from datetime import date
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestSubscriptionDates(TransactionCase):
    """Échéances : fin de mois, années bissextiles."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Plan = cls.env["sale.subscription.plan"]
        cls.plan_month = Plan.create({"name": "M", "billing_unit": "month"})
        cls.plan_quarter = Plan.create(
            {"name": "T", "billing_unit": "month", "billing_interval": 3}
        )
        cls.plan_year = Plan.create({"name": "A", "billing_unit": "year"})

    def _chain(self, plan, start, count):
        dates, current = [], start
        for _ in range(count):
            current = plan._get_next_date(current, anchor=start)
            dates.append(current)
        return dates

    def test_month_end_comes_back_to_31(self):
        # 31/01 -> 28/02 -> 31/03 (et non 28/03 : pas de glissement)
        self.assertEqual(
            self._chain(self.plan_month, date(2026, 1, 31), 4),
            [date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30), date(2026, 5, 31)],
        )

    def test_month_end_leap_year(self):
        self.assertEqual(
            self._chain(self.plan_month, date(2028, 1, 31), 2),
            [date(2028, 2, 29), date(2028, 3, 31)],
        )

    def test_day_30_keeps_30(self):
        self.assertEqual(
            self._chain(self.plan_month, date(2026, 1, 30), 3),
            [date(2026, 2, 28), date(2026, 3, 30), date(2026, 4, 30)],
        )

    def test_quarterly_from_31(self):
        self.assertEqual(
            self._chain(self.plan_quarter, date(2025, 11, 30), 2),
            [date(2026, 2, 28), date(2026, 5, 30)],
        )

    def test_yearly_from_29_february(self):
        self.assertEqual(
            self._chain(self.plan_year, date(2024, 2, 29), 4),
            [date(2025, 2, 28), date(2026, 2, 28), date(2027, 2, 28), date(2028, 2, 29)],
        )

    def test_without_anchor_month_end_stays_month_end(self):
        self.assertEqual(
            self.plan_month._get_next_date(date(2026, 2, 28)), date(2026, 3, 31)
        )
        self.assertEqual(
            self.plan_month._get_next_date(date(2026, 1, 15)), date(2026, 2, 15)
        )

    def test_off_grid_date_ignores_anchor(self):
        # échéance déplacée à la main : on repart d'elle, pas du début
        self.assertEqual(
            self.plan_month._get_next_date(date(2026, 3, 10), anchor=date(2026, 1, 20)),
            date(2026, 4, 10),
        )


class TestSubscriptionBilling(TransactionCase):
    """Facturation : pas de doublon, cron idempotent, échecs annulés."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan = cls.env["sale.subscription.plan"].create(
            {"name": "M", "billing_unit": "month"}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Client Règles"})
        cls.product = cls.env["product.product"].create(
            {"name": "Service Règles", "type": "service", "list_price": 10.0}
        )

    def _sub(self, start=date(2026, 1, 31), next_date=None, plan=None):
        sub = self.env["sale.subscription"].create(
            {
                "partner_id": self.partner.id,
                "plan_id": (plan or self.plan).id,
                "line_ids": [
                    Command.create(
                        {"product_id": self.product.id, "name": "L", "price_unit": 10.0}
                    )
                ],
            }
        )
        sub.action_start()
        sub.write({"date_start": start, "next_invoice_date": next_date or start})
        return sub

    def test_invoicing_chain_month_end(self):
        sub = self._sub()
        for _ in range(3):
            sub._generate_invoice()
        self.assertEqual(sub.next_invoice_date, date(2026, 4, 30))
        self.assertEqual(len(sub.invoice_ids), 3)

    def test_cron_twice_same_day_bills_once(self):
        today = fields.Date.today()
        sub = self._sub(start=today)
        Sub = self.env["sale.subscription"]
        Sub._cron_generate_invoices()
        Sub._cron_generate_invoices()  # relance le même jour : rien de plus
        self.assertEqual(len(sub.invoice_ids), 1)
        self.assertEqual(sub.next_invoice_date, self.plan._get_next_date(today, anchor=today))

    def test_cron_catches_up_one_period_per_pass(self):
        sub = self._sub(start=date(2020, 1, 31))
        Sub = self.env["sale.subscription"]
        Sub._cron_generate_invoices()
        Sub._cron_generate_invoices()
        self.assertEqual(len(sub.invoice_ids), 2)
        self.assertEqual(sub.next_invoice_date, date(2020, 3, 31))

    def test_cron_failure_leaves_no_orphan_invoice(self):
        plan = self.env["sale.subscription.plan"].create(
            {"name": "Auto", "billing_unit": "month", "auto_post_invoice": True}
        )
        failing = self._sub(start=date(2020, 1, 15), plan=plan)
        ok = self._sub(start=date(2020, 1, 15))
        failing_name = failing.name
        Move = self.env.registry["account.move"]
        original_post = Move.action_post

        def action_post(moves):
            if any(m.invoice_origin == failing_name for m in moves):
                raise UserError("échec simulé")
            return original_post(moves)

        with patch.object(Move, "action_post", action_post), self.assertLogs(
            "odoo.addons.oski_subscription.models.sale_subscription", "ERROR"
        ):
            self.env["sale.subscription"]._cron_generate_invoices()
        orphans = self.env["account.move"].search([("invoice_origin", "=", failing_name)])
        self.assertFalse(orphans, "la facture d'un abonnement en échec doit être annulée")
        self.assertEqual(failing.next_invoice_date, date(2020, 1, 15))
        self.assertEqual(len(ok.invoice_ids), 1)

    def test_refuse_closed_subscription(self):
        sub = self._sub()
        sub.action_close()
        with self.assertRaises(UserError):
            sub._generate_invoice()
        self.assertFalse(sub.invoice_ids)

    def test_never_bills_beyond_engagement(self):
        sub = self._sub(start=date(2020, 1, 15))
        sub.date_end = date(2020, 1, 31)
        sub._generate_invoice()  # période du 15/01 : couverte, puis résiliation
        self.assertEqual(sub.state, "closed")
        sub.state = "progress"  # réouvert à la main sans prolonger l'engagement
        with self.assertRaises(UserError):
            sub._generate_invoice()
        self.env["sale.subscription"]._cron_generate_invoices()
        self.assertEqual(len(sub.invoice_ids), 1)

    def test_refuse_without_lines(self):
        sub = self._sub()
        sub.line_ids.unlink()
        with self.assertRaises(UserError):
            sub._generate_invoice()


@tagged("post_install", "-at_install")
class TestSubscriptionMultiCompany(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # l'utilisateur comptable du socle de test gère aussi les abonnements
        cls.env.user.groups_id |= cls.env.ref(
            "oski_subscription.group_subscription_manager"
        )
        cls.company_a = cls.env.company
        cls.company_b = cls.setup_other_company()["company"]
        cls.plan = cls.env["sale.subscription.plan"].create(
            {"name": "M", "billing_unit": "month"}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Client MC"})
        cls.product = cls.env["product.product"].create(
            {"name": "Service MC", "type": "service", "list_price": 10.0}
        )
        cls.sub_b = cls.env["sale.subscription"].create(
            {
                "partner_id": cls.partner.id,
                "plan_id": cls.plan.id,
                "company_id": cls.company_b.id,
                "line_ids": [
                    Command.create(
                        {"product_id": cls.product.id, "name": "L", "price_unit": 10.0}
                    )
                ],
            }
        )

    def test_invoice_in_subscription_company(self):
        # société courante = A, B seulement autorisée : la facture doit
        # quand même naître dans la société de l'abonnement
        sub = self.sub_b.with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id]
        )
        sub.action_start()
        move = sub._generate_invoice()
        self.assertEqual(move.company_id, self.company_b)
        self.assertEqual(move.journal_id.company_id, self.company_b)

    def test_user_of_other_company_does_not_see(self):
        user = self.env["res.users"].create(
            {
                "name": "Sub User A",
                "login": "sub_user_a_mc",
                "company_id": self.company_a.id,
                "company_ids": [Command.set(self.company_a.ids)],
                "groups_id": [
                    Command.set(
                        [self.env.ref("oski_subscription.group_subscription_user").id]
                    )
                ],
            }
        )
        Sub = self.env["sale.subscription"].with_user(user)
        self.assertNotIn(self.sub_b, Sub.search([]))
        with self.assertRaises(AccessError):
            self.sub_b.with_user(user).read(["mrr"])
        with self.assertRaises(AccessError):
            self.sub_b.line_ids.with_user(user).read(["price_unit"])

    def test_product_taxes_filtered_by_company(self):
        tax_b = self.env["account.tax"].create(
            {"name": "TVA B", "amount": 19.0, "company_id": self.company_b.id}
        )
        tax_a = self.env["account.tax"].create(
            {"name": "TVA A", "amount": 20.0, "company_id": self.company_a.id}
        )
        product = self.env["product.product"].create(
            {"name": "P taxes", "taxes_id": [Command.set((tax_a | tax_b).ids)]}
        )
        line = self.env["sale.subscription.line"].new(
            {"subscription_id": self.sub_b.id, "product_id": product.id}
        )
        line._onchange_product_id()
        self.assertEqual(line.tax_ids._origin, tax_b)
