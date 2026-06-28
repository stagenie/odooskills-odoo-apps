from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSubscription(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Plan = cls.env["sale.subscription.plan"]
        cls.plan_month = cls.Plan.create({"name": "Mensuel", "billing_unit": "month"})
        cls.plan_year = cls.Plan.create({"name": "Annuel", "billing_unit": "year"})

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
