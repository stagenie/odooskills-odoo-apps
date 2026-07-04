from datetime import datetime

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

START = datetime(2026, 8, 1, 8, 0)
STOP = datetime(2026, 8, 5, 8, 0)


@tagged('post_install', '-at_install')
class TestRentalInvoice(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # AccountTestInvoicingCommon bascule cls.env sur un utilisateur de test
        # non-superuser ("accountman") : il lui manque le groupe métier Location.
        cls.env.user.group_ids += cls.env.ref('oski_rental.group_rental_manager')
        cls.asset = cls.env['oski.rental.asset'].create({
            'name': 'Asset Facture', 'price_day': 100.0, 'deposit_amount': 200.0,
        })

    def _returned_order(self, late_amount=0.0):
        order = self.env['oski.rental.order'].create({
            'partner_id': self.partner_a.id,
            'date_start': START, 'date_end': STOP,
            'line_ids': [(0, 0, {
                'asset_id': self.asset.id,
                'date_start': START, 'date_end': STOP,
            })],
        })
        order.action_reserve()
        checkout = self.env['oski.rental.checkout.wizard'].create({
            'order_id': order.id, 'deposit_collected': True})
        checkout.action_validate()
        checkin = self.env['oski.rental.checkin.wizard'].create({
            'order_id': order.id, 'actual_return_date': STOP,
            'invoice_late': False})
        checkin.action_validate()
        if late_amount:
            order.line_ids.late_amount = late_amount
        return order

    def test_invoice_created(self):
        order = self._returned_order()
        order.action_create_invoice()
        self.assertEqual(order.state, 'done')
        self.assertEqual(len(order.invoice_ids), 1)
        move = order.invoice_ids
        self.assertEqual(move.move_type, 'out_invoice')
        self.assertEqual(move.state, 'draft')
        self.assertEqual(move.invoice_origin, order.name)
        self.assertEqual(len(move.invoice_line_ids), 1)
        self.assertEqual(move.invoice_line_ids.price_unit, 400.0)

    def test_invoice_late_line(self):
        order = self._returned_order(late_amount=150.0)
        order.action_create_invoice()
        move = order.invoice_ids
        self.assertEqual(len(move.invoice_line_ids), 2)
        late_line = move.invoice_line_ids.filtered(
            lambda l: 'Retard' in (l.name or ''))
        self.assertEqual(late_line.price_unit, 150.0)

    def test_invoice_wrong_state(self):
        order = self.env['oski.rental.order'].create({
            'partner_id': self.partner_a.id,
            'date_start': START, 'date_end': STOP,
            'line_ids': [(0, 0, {
                'asset_id': self.asset.id,
                'date_start': START, 'date_end': STOP,
            })],
        })
        with self.assertRaises(UserError):
            order.action_create_invoice()

    def test_refund_deposit(self):
        order = self._returned_order()
        self.assertEqual(order.deposit_state, 'collected')
        order.action_refund_deposit()
        self.assertEqual(order.deposit_state, 'refunded')

    def test_refund_deposit_wrong_state(self):
        order = self._returned_order()
        order.deposit_state = 'to_collect'
        with self.assertRaises(UserError):
            order.action_refund_deposit()
