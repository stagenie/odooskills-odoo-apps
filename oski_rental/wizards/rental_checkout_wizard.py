from odoo import fields, models
from odoo.exceptions import UserError


class RentalCheckoutWizard(models.TransientModel):
    _name = 'oski.rental.checkout.wizard'
    _description = 'Départ de location'

    order_id = fields.Many2one('oski.rental.order', required=True)
    checkout_note = fields.Text(string='État des lieux — départ')
    deposit_collected = fields.Boolean(string='Caution perçue')
    deposit_total = fields.Monetary(related='order_id.deposit_total')
    currency_id = fields.Many2one(related='order_id.currency_id')

    def action_validate(self):
        self.ensure_one()
        order = self.order_id
        if order.state != 'reserved':
            raise UserError("Seule une location réservée peut partir.")
        if order.deposit_total and not self.deposit_collected:
            raise UserError(
                "Confirmez la perception de la caution (%s) avant le départ."
                % order.deposit_total)
        order.write({
            'state': 'ongoing',
            'checkout_note': self.checkout_note,
            'deposit_state': 'collected' if order.deposit_total else 'none',
        })
