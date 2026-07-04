from datetime import datetime

from odoo.exceptions import UserError

from .common import RentalCase

START = datetime(2026, 8, 1, 8, 0)
STOP = datetime(2026, 8, 5, 8, 0)


class TestCheckoutCheckin(RentalCase):

    def _reserved_order(self, deposit=0.0):
        asset = self._make_asset(deposit_amount=deposit)
        order = self._make_order([asset], START, STOP)
        order.action_reserve()
        return order

    def _checkout(self, order, **kw):
        vals = {'order_id': order.id}
        vals.update(kw)
        wizard = self.env['oski.rental.checkout.wizard'].create(vals)
        wizard.action_validate()
        return wizard

    def _checkin(self, order, return_date=STOP, **kw):
        vals = {'order_id': order.id, 'actual_return_date': return_date}
        vals.update(kw)
        wizard = self.env['oski.rental.checkin.wizard'].create(vals)
        wizard.action_validate()
        return wizard

    def test_checkout_ok(self):
        order = self._reserved_order()
        self._checkout(order, checkout_note='RAS')
        self.assertEqual(order.state, 'ongoing')
        self.assertEqual(order.checkout_note, 'RAS')

    def test_checkout_requires_deposit_confirmation(self):
        order = self._reserved_order(deposit=200)
        with self.assertRaises(UserError):
            self._checkout(order)
        self._checkout(order, deposit_collected=True)
        self.assertEqual(order.deposit_state, 'collected')

    def test_checkout_wrong_state(self):
        order = self._make_order([self._make_asset()], START, STOP)
        with self.assertRaises(UserError):
            self._checkout(order)

    def test_checkin_on_time(self):
        order = self._reserved_order()
        self._checkout(order)
        self._checkin(order, checkin_note='OK')
        self.assertEqual(order.state, 'returned')
        self.assertEqual(order.actual_return_date, STOP)
        self.assertFalse(order.is_late)
        self.assertEqual(sum(order.line_ids.mapped('late_amount')), 0.0)

    def test_checkin_late_with_invoicing(self):
        order = self._reserved_order()
        self._checkout(order)
        # retour 2 jours après la fin prévue, jour = 100
        self._checkin(order, return_date=datetime(2026, 8, 7, 8, 0),
                      invoice_late=True)
        self.assertTrue(order.is_late)
        self.assertEqual(order.line_ids.late_amount, 200.0)
        self.assertEqual(order.amount_total, order.amount_subtotal + 200.0)

    def test_checkin_late_without_invoicing(self):
        order = self._reserved_order()
        self._checkout(order)
        self._checkin(order, return_date=datetime(2026, 8, 7, 8, 0),
                      invoice_late=False)
        self.assertTrue(order.is_late)
        self.assertEqual(order.line_ids.late_amount, 0.0)

    def test_checkin_before_start_forbidden(self):
        order = self._reserved_order()
        self._checkout(order)
        with self.assertRaises(UserError):
            self._checkin(order, return_date=datetime(2026, 7, 30))
