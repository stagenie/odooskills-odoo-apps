from odoo import fields, models
from odoo.exceptions import UserError


class RentalCheckinWizard(models.TransientModel):
    _name = 'oski.rental.checkin.wizard'
    _description = 'Retour de location'

    order_id = fields.Many2one('oski.rental.order', required=True)
    actual_return_date = fields.Datetime(
        string='Retour effectif', required=True,
        default=fields.Datetime.now)
    checkin_note = fields.Text(string='État des lieux — retour')
    invoice_late = fields.Boolean(
        string='Facturer le retard',
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'oski_rental.late_invoicing') == 'True')

    def action_validate(self):
        self.ensure_one()
        order = self.order_id
        if order.state != 'ongoing':
            raise UserError("Seule une location en cours peut être retournée.")
        if self.actual_return_date <= order.date_start:
            raise UserError("Le retour ne peut pas précéder le départ.")
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
