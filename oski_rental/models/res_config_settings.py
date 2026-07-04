from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rental_default_product_id = fields.Many2one(
        'product.product', string='Article de facturation location',
        domain=[('type', '=', 'service')],
        config_parameter='oski_rental.default_product_id')
    rental_late_invoicing = fields.Boolean(
        string='Facturer les retards par défaut',
        config_parameter='oski_rental.late_invoicing')
    rental_min_granularity = fields.Selection([
        ('hour', 'Heure'),
        ('day', 'Jour'),
    ], string='Granularité minimale', default='hour',
        config_parameter='oski_rental.min_granularity')
