from odoo import fields, models
from odoo.exceptions import UserError


class RentalCheckinWizard(models.TransientModel):
    _name = 'oski.rental.checkin.wizard'
    _description = 'Rental Return'

    order_id = fields.Many2one('oski.rental.order', required=True)
    actual_return_date = fields.Datetime(
        string='Actual Return', required=True,
        default=fields.Datetime.now)
    checkin_note = fields.Text(string='Condition Report: Return')
    invoice_late = fields.Boolean(
        string='Invoice Late Return',
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'oski_rental.late_invoicing') == 'True')

    def action_validate(self):
        self.ensure_one()
        order = self.order_id
        if order.state != 'ongoing':
            raise UserError(self.env._("Only an ongoing rental can be returned."))
        if self.actual_return_date <= order.date_start:
            raise UserError(self.env._("The return cannot precede the pickup."))
        if self.invoice_late:
            for line in order.line_ids:
                if self.actual_return_date > line.date_end:
                    line.late_amount = line.asset_id._get_rental_price(
                        line.date_end, self.actual_return_date)
        order.write({
            'state': 'returned',
            'actual_return_date': self.actual_return_date,
            'checkin_note': self.checkin_note,
        })
