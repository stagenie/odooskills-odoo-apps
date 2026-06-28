from datetime import date

from odoo import Command
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
