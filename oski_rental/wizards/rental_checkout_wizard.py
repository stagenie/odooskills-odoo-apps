from odoo import fields, models
from odoo.exceptions import UserError


class RentalCheckoutWizard(models.TransientModel):
    _name = 'oski.rental.checkout.wizard'
    _description = 'Rental Pickup'

    order_id = fields.Many2one('oski.rental.order', required=True)
    checkout_note = fields.Text(string='Condition Report: Pickup')
    deposit_collected = fields.Boolean(string='Deposit Collected')
    deposit_total = fields.Monetary(related='order_id.deposit_total')
    currency_id = fields.Many2one(related='order_id.currency_id')

    def action_validate(self):
        self.ensure_one()
        order = self.order_id
        if order.state != 'reserved':
            raise UserError(self.env._("Only a reserved rental can be picked up."))
        if order.deposit_total and not self.deposit_collected:
            raise UserError(
                self.env._(
                    "Confirm that the deposit (%s) has been collected before pickup.",
                    order.deposit_total))
        order.write({
            'state': 'ongoing',
            'checkout_note': self.checkout_note,
            'deposit_state': 'collected' if order.deposit_total else 'none',
        })
