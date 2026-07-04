from odoo import api, fields, models
from odoo.exceptions import ValidationError


class RentalOrderLine(models.Model):
    _name = 'oski.rental.order.line'
    _description = 'Ligne de location'

    order_id = fields.Many2one(
        'oski.rental.order', string='Location', required=True, ondelete='cascade')
    asset_id = fields.Many2one(
        'oski.rental.asset', string='Ressource', required=True)
    date_start = fields.Datetime(string='Début', required=True)
    date_end = fields.Datetime(string='Fin', required=True)
    price_unit = fields.Monetary(
        string='Prix', compute='_compute_price_unit', store=True, readonly=False)
    price_subtotal = fields.Monetary(
        string='Sous-total', compute='_compute_price_subtotal', store=True)
    deposit = fields.Monetary(
        string='Caution', compute='_compute_deposit', store=True, readonly=False)
    late_amount = fields.Monetary(string='Montant retard', copy=False)
    state = fields.Selection(related='order_id.state', store=True)
    company_id = fields.Many2one(related='order_id.company_id', store=True)
    currency_id = fields.Many2one(related='order_id.currency_id')

    @api.depends('asset_id', 'date_start', 'date_end')
    def _compute_price_unit(self):
        for line in self:
            if line.asset_id and line.date_start and line.date_end \
                    and line.date_end > line.date_start:
                line.price_unit = line.asset_id._get_rental_price(
                    line.date_start, line.date_end)
            else:
                line.price_unit = 0.0

    @api.depends('price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.price_unit

    @api.depends('asset_id')
    def _compute_deposit(self):
        for line in self:
            line.deposit = line.asset_id.deposit_amount

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for line in self:
            if line.date_end <= line.date_start:
                raise ValidationError(
                    "La date de fin doit être postérieure à la date de début.")
