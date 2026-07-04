from datetime import datetime

from odoo.exceptions import UserError

from .common import RentalCase

START = datetime(2026, 8, 1, 8, 0)
STOP = datetime(2026, 8, 5, 8, 0)


class TestTransitions(RentalCase):

    def test_reserve_ok(self):
        asset = self._make_asset(deposit_amount=200)
        order = self._make_order([asset], START, STOP)
        order.action_reserve()
        self.assertEqual(order.state, 'reserved')
        self.assertEqual(order.deposit_state, 'to_collect')

    def test_reserve_no_deposit(self):
        order = self._make_order([self._make_asset()], START, STOP)
        order.action_reserve()
        self.assertEqual(order.deposit_state, 'none')

    def test_reserve_requires_lines(self):
        order = self.env['oski.rental.order'].create({
            'partner_id': self.partner.id,
            'date_start': START, 'date_end': STOP,
        })
        with self.assertRaises(UserError):
            order.action_reserve()

    def test_reserve_conflict_other_order(self):
        asset = self._make_asset()
        self._make_order([asset], START, STOP).action_reserve()
        clash = self._make_order(
            [asset], datetime(2026, 8, 3), datetime(2026, 8, 7))
        with self.assertRaises(UserError):
            clash.action_reserve()

    def test_reserve_conflict_unavailability(self):
        asset = self._make_asset()
        self.env['oski.rental.unavailability'].create({
            'asset_id': asset.id,
            'date_start': datetime(2026, 8, 2),
            'date_end': datetime(2026, 8, 3),
            'reason': 'maintenance',
        })
        order = self._make_order([asset], START, STOP)
        with self.assertRaises(UserError):
            order.action_reserve()

    def test_reserve_conflict_intra_order(self):
        asset = self._make_asset()
        order = self._make_order([asset], START, STOP)
        order.line_ids = [(0, 0, {
            'asset_id': asset.id,
            'date_start': datetime(2026, 8, 4),
            'date_end': datetime(2026, 8, 6),
        })]
        with self.assertRaises(UserError):
            order.action_reserve()

    def test_back_to_back_ok(self):
        # bords exclusifs : une résa finit pile quand l'autre commence
        asset = self._make_asset()
        self._make_order([asset], START, STOP).action_reserve()
        follow = self._make_order([asset], STOP, datetime(2026, 8, 9))
        follow.action_reserve()
        self.assertEqual(follow.state, 'reserved')

    def test_cancel_only_draft_reserved(self):
        order = self._make_order([self._make_asset()], START, STOP)
        order.action_reserve()
        order.action_cancel()
        self.assertEqual(order.state, 'cancelled')
        order2 = self._make_order([self._make_asset(name='A2')], START, STOP)
        order2.state = 'ongoing'
        with self.assertRaises(UserError):
            order2.action_cancel()

    def test_cancelled_frees_asset(self):
        asset = self._make_asset()
        first = self._make_order([asset], START, STOP)
        first.action_reserve()
        first.action_cancel()
        second = self._make_order([asset], START, STOP)
        second.action_reserve()
        self.assertEqual(second.state, 'reserved')
