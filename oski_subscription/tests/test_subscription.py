from datetime import date

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSubscription(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Plan = cls.env["sale.subscription.plan"]
        cls.plan_month = cls.Plan.create({"name": "Mensuel", "billing_unit": "month"})
        cls.plan_year = cls.Plan.create({"name": "Annuel", "billing_unit": "year"})
        cls.partner = cls.env["res.partner"].create({"name": "Client Sub"})
        cls.product = cls.env["product.product"].create(
            {"name": "Service Sub", "type": "service", "list_price": 100.0}
        )

    def _make_sub(self, plan=None, lines=None):
        plan = plan or self.plan_month
        lines = lines or [(1, 100.0, 0.0)]
        return self.env["sale.subscription"].create(
            {
                "partner_id": self.partner.id,
                "plan_id": plan.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "name": "L",
                            "quantity": q,
                            "price_unit": p,
                            "discount": d,
                        }
                    )
                    for (q, p, d) in lines
                ],
            }
        )

    def test_next_date_month(self):
        self.assertEqual(
            self.plan_month._get_next_date(date(2026, 1, 15)), date(2026, 2, 15)
        )

    def test_next_date_year(self):
        self.assertEqual(
            self.plan_year._get_next_date(date(2026, 1, 15)), date(2027, 1, 15)
        )

    def test_next_date_week(self):
        plan = self.Plan.create({"name": "Hebdo", "billing_unit": "week"})
        self.assertEqual(plan._get_next_date(date(2026, 1, 1)), date(2026, 1, 8))

    def test_next_date_day_interval(self):
        plan = self.Plan.create(
            {"name": "3 jours", "billing_unit": "day", "billing_interval": 3}
        )
        self.assertEqual(plan._get_next_date(date(2026, 1, 1)), date(2026, 1, 4))

    def test_interval_constraint(self):
        with self.assertRaises(ValidationError):
            self.Plan.create({"name": "Bad", "billing_interval": 0})

    def test_recurring_total(self):
        sub = self._make_sub(lines=[(2, 50.0, 0.0), (1, 30.0, 10.0)])
        # 2*50 + 1*30*0.9 = 100 + 27 = 127
        self.assertAlmostEqual(sub.recurring_total, 127.0)

    def test_mrr_monthly(self):
        sub = self._make_sub(lines=[(1, 100.0, 0.0)])
        self.assertAlmostEqual(sub.mrr, 100.0)

    def test_mrr_yearly(self):
        sub = self._make_sub(plan=self.plan_year, lines=[(1, 120.0, 0.0)])
        self.assertAlmostEqual(sub.mrr, 10.0)

    def test_mrr_weekly(self):
        plan = self.Plan.create({"name": "Hebdo", "billing_unit": "week"})
        sub = self._make_sub(plan=plan, lines=[(1, 10.0, 0.0)])
        # 10 * 30/7 = 42.857
        self.assertAlmostEqual(sub.mrr, 10.0 * 30.0 / 7.0, places=2)

    def test_date_constraint(self):
        with self.assertRaises(ValidationError):
            sub = self._make_sub()
            sub.write({"date_start": date(2026, 5, 1), "date_end": date(2026, 1, 1)})

    def test_action_start(self):
        sub = self._make_sub()
        sub.action_start()
        self.assertEqual(sub.state, "progress")
        self.assertEqual(sub.date_start, fields.Date.today())
        self.assertEqual(sub.next_invoice_date, fields.Date.today())
        self.assertTrue(sub.name.startswith("SUB/"))

    def test_pause_resume(self):
        sub = self._make_sub()
        sub.action_start()
        sub.action_pause()
        self.assertEqual(sub.state, "paused")
        sub.next_invoice_date = date(2020, 1, 1)
        sub.action_resume()
        self.assertEqual(sub.state, "progress")
        self.assertEqual(sub.next_invoice_date, fields.Date.today())

    def test_close(self):
        sub = self._make_sub()
        sub.action_start()
        sub.action_close()
        self.assertEqual(sub.state, "closed")
        self.assertEqual(sub.date_closed, fields.Date.today())

    def test_generate_invoice_draft(self):
        sub = self._make_sub(lines=[(2, 50.0, 0.0)])
        sub.action_start()
        move = sub._generate_invoice()
        self.assertEqual(move.move_type, "out_invoice")
        self.assertEqual(move.partner_id, self.partner)
        self.assertEqual(move.state, "draft")
        self.assertEqual(len(move.invoice_line_ids), 1)
        self.assertAlmostEqual(move.invoice_line_ids.price_unit, 50.0)
        self.assertIn(move, sub.invoice_ids)
        # facturation d'avance : démarrée aujourd'hui, prochaine = +1 mois
        self.assertEqual(
            sub.next_invoice_date, self.plan_month._get_next_date(fields.Date.today())
        )

    def test_generate_invoice_autopost(self):
        plan = self.Plan.create(
            {"name": "Auto", "billing_unit": "month", "auto_post_invoice": True}
        )
        sub = self._make_sub(plan=plan)
        sub.action_start()
        move = sub._generate_invoice()
        self.assertEqual(move.state, "posted")

    def test_generate_invoice_closes_on_date_end(self):
        sub = self._make_sub()
        sub.action_start()
        sub.date_end = fields.Date.today()  # toute prochaine échéance dépasse
        sub._generate_invoice()
        self.assertEqual(sub.state, "closed")

    def test_cron_only_due_progress(self):
        SaleSub = self.env["sale.subscription"]
        # éligible : progress + échu
        due = self._make_sub()
        due.action_start()
        due.next_invoice_date = date(2020, 1, 1)
        # non éligible : progress mais futur
        future = self._make_sub()
        future.action_start()
        future.next_invoice_date = date(2999, 1, 1)
        # non éligible : draft
        draft = self._make_sub()
        # non éligible : paused échu
        paused = self._make_sub()
        paused.action_start()
        paused.next_invoice_date = date(2020, 1, 1)
        paused.action_pause()

        SaleSub._cron_generate_invoices()

        self.assertEqual(len(due.invoice_ids), 1)
        self.assertEqual(len(future.invoice_ids), 0)
        self.assertEqual(len(draft.invoice_ids), 0)
        self.assertEqual(len(paused.invoice_ids), 0)

    def test_access_user_cannot_create_plan(self):
        from odoo.exceptions import AccessError
        user = self.env["res.users"].create(
            {
                "name": "Sub User",
                "login": "sub_user",
                "group_ids": [
                    Command.set([self.env.ref("oski_subscription.group_subscription_user").id])
                ],
            }
        )
        with self.assertRaises(AccessError):
            self.env["sale.subscription.plan"].with_user(user).create(
                {"name": "X", "billing_unit": "month"}
            )

    def test_access_manager_can_create_plan(self):
        manager = self.env["res.users"].create(
            {
                "name": "Sub Mgr",
                "login": "sub_mgr",
                "group_ids": [
                    Command.set([self.env.ref("oski_subscription.group_subscription_manager").id])
                ],
            }
        )
        plan = self.env["sale.subscription.plan"].with_user(manager).create(
            {"name": "Mgr Plan", "billing_unit": "month"}
        )
        self.assertTrue(plan.id)
