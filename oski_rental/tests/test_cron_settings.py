from datetime import datetime, timedelta

from odoo import fields

from .common import RentalCase


class TestCronSettings(RentalCase):

    def _ongoing_overdue_order(self):
        asset = self._make_asset()
        start = fields.Datetime.now() - timedelta(days=5)
        stop = fields.Datetime.now() - timedelta(days=1)
        order = self._make_order([asset], start, stop)
        order.action_reserve()
        checkout = self.env['oski.rental.checkout.wizard'].create({
            'order_id': order.id})
        checkout.action_validate()
        return order

    def test_cron_flags_and_activity(self):
        order = self._ongoing_overdue_order()
        self.assertTrue(order.is_late)
        self.env['oski.rental.order']._cron_late_alert()
        self.assertTrue(order.late_notified)
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'oski.rental.order'),
            ('res_id', '=', order.id),
        ])
        self.assertEqual(len(activities), 1)

    def test_cron_idempotent(self):
        order = self._ongoing_overdue_order()
        self.env['oski.rental.order']._cron_late_alert()
        self.env['oski.rental.order']._cron_late_alert()
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'oski.rental.order'),
            ('res_id', '=', order.id),
        ])
        self.assertEqual(len(activities), 1)

    def test_cron_ignores_future(self):
        asset = self._make_asset()
        start = fields.Datetime.now() + timedelta(days=1)
        stop = fields.Datetime.now() + timedelta(days=3)
        order = self._make_order([asset], start, stop)
        order.action_reserve()
        self.env['oski.rental.order']._cron_late_alert()
        self.assertFalse(order.late_notified)

    def test_settings_roundtrip(self):
        settings = self.env['res.config.settings'].create({
            'rental_late_invoicing': True,
            'rental_min_granularity': 'day',
        })
        settings.execute()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        self.assertEqual(get_param('oski_rental.late_invoicing'), 'True')
        self.assertEqual(get_param('oski_rental.min_granularity'), 'day')
