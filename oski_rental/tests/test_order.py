from datetime import datetime

from odoo.exceptions import UserError

from .common import RentalCase

START = datetime(2026, 8, 1, 8, 0)
STOP = datetime(2026, 8, 11, 8, 0)  # 10 jours


class TestOrder(RentalCase):

    def test_sequence_and_defaults(self):
        order = self._make_order([self._make_asset()], START, STOP)
        self.assertTrue(order.name.startswith('OSKR/'))
        self.assertEqual(order.state, 'draft')
        self.assertEqual(order.deposit_state, 'none')

    def test_line_price_computed(self):
        # jour 100 / semaine 500 → 10 jours = 800
        order = self._make_order([self._make_asset()], START, STOP)
        self.assertEqual(order.line_ids.price_unit, 800.0)
        self.assertEqual(order.amount_subtotal, 800.0)

    def test_price_override_kept(self):
        order = self._make_order([self._make_asset()], START, STOP)
        order.line_ids.price_unit = 750.0
        self.assertEqual(order.amount_subtotal, 750.0)

    def test_deposit_totals(self):
        a1 = self._make_asset(deposit_amount=200)
        a2 = self._make_asset(name='Asset 2', deposit_amount=300)
        order = self._make_order([a1, a2], START, STOP)
        self.assertEqual(order.deposit_total, 500.0)

    def test_amount_total_includes_late(self):
        order = self._make_order([self._make_asset()], START, STOP)
        order.line_ids.late_amount = 100.0
        self.assertEqual(order.amount_total, 900.0)

    def test_unlink_only_draft_cancelled(self):
        order = self._make_order([self._make_asset()], START, STOP)
        order.state = 'reserved'
        with self.assertRaises(UserError):
            order.unlink()
        order.state = 'draft'
        order.unlink()
