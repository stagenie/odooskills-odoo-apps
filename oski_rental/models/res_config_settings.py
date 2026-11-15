from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rental_default_product_id = fields.Many2one(
        'product.product', string='Rental Invoicing Product',
        domain=[('type', '=', 'service')],
        config_parameter='oski_rental.default_product_id')
    rental_late_invoicing = fields.Boolean(
        string='Invoice Late Returns by Default',
        config_parameter='oski_rental.late_invoicing')
    rental_min_granularity = fields.Selection([
        ('hour', 'Hour'),
        ('day', 'Day'),
    ], string='Minimum Granularity', default='hour',
        config_parameter='oski_rental.min_granularity')
