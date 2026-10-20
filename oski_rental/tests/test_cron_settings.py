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
        icp = self.env['ir.config_parameter'].sudo()
        self.assertIs(icp.get_bool('oski_rental.late_invoicing'), True)
        self.assertEqual(icp.get_str('oski_rental.min_granularity'), 'day')

    def test_cron_note_local_time(self):
        self.env.company.partner_id.tz = 'Europe/Paris'
        order = self._ongoing_overdue_order()
        self.env['oski.rental.order']._cron_late_alert()
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'oski.rental.order'),
            ('res_id', '=', order.id),
        ])
        expected = fields.Datetime.context_timestamp(
            order.with_context(tz='Europe/Paris'), order.date_end
        ).strftime('%d/%m/%Y %H:%M')
        self.assertIn(expected, str(activity.note))

    def test_checkin_default_follows_setting(self):
        """Le réglage « Facturer les retards par défaut » pré-coche le retour."""
        order = self._ongoing_overdue_order()
        wizard_model = self.env['oski.rental.checkin.wizard']
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_bool('oski_rental.late_invoicing', True)
        self.assertTrue(wizard_model.create({'order_id': order.id}).invoice_late)
        icp.set_bool('oski_rental.late_invoicing', False)
        self.assertFalse(wizard_model.create({'order_id': order.id}).invoice_late)

    def test_default_product_from_setting(self):
        """L'article choisi dans les paramètres prime sur l'article livré."""
        product = self.env['product.product'].create({
            'name': 'Location configurée', 'type': 'service'})
        self.env['res.config.settings'].create({
            'rental_default_product_id': product.id}).execute()
        order = self.env['oski.rental.order']
        self.assertEqual(order._get_default_rental_product(), product)
        product.unlink()
        self.assertEqual(
            order._get_default_rental_product(),
            self.env.ref('oski_rental.product_rental_default'))
