from datetime import timedelta

from odoo import api, fields, models


PRICE_TIERS = [
    ('price_month', 30 * 86400),
    ('price_week', 7 * 86400),
    ('price_day', 86400),
    ('price_hour', 3600),
]


class RentalAsset(models.Model):
    _name = 'oski.rental.asset'
    _description = 'Ressource de location'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Nom', required=True, tracking=True)
    code = fields.Char(string='Code', readonly=True, copy=False, default='Nouveau')
    category_id = fields.Many2one('oski.rental.category', string='Catégorie')
    image_1920 = fields.Image(string='Image')
    description = fields.Html(string='Description')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Société', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    price_hour = fields.Monetary(string='Prix / heure')
    price_day = fields.Monetary(string='Prix / jour')
    price_week = fields.Monetary(string='Prix / semaine')
    price_month = fields.Monetary(string='Prix / mois')
    deposit_amount = fields.Monetary(string='Caution')
    product_id = fields.Many2one(
        'product.product', string='Article de facturation',
        domain=[('type', '=', 'service')],
        help="Article porté sur les lignes de facture. "
             "À défaut, l'article configuré dans les paramètres est utilisé.")
    is_available_now = fields.Boolean(
        string='Disponible', compute='_compute_is_available_now')
    order_line_ids = fields.One2many('oski.rental.order.line', 'asset_id')
    order_count = fields.Integer(compute='_compute_counts')
    unavailability_ids = fields.One2many('oski.rental.unavailability', 'asset_id')
    unavailability_count = fields.Integer(compute='_compute_counts')

    _code_company_uniq = models.Constraint(
        'UNIQUE (code, company_id)',
        "Ce code de ressource est déjà utilisé.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') or vals['code'] == 'Nouveau':
                vals['code'] = self.env['ir.sequence'].sudo().next_by_code(
                    'oski.rental.asset') or 'Nouveau'
        return super().create(vals_list)

    def _compute_is_available_now(self):
        now = fields.Datetime.now()
        for asset in self:
            asset.is_available_now = asset.check_availability(
                now, now + timedelta(hours=1))

    def _compute_counts(self):
        for asset in self:
            asset.order_count = len(asset.order_line_ids.mapped('order_id'))
            asset.unavailability_count = len(asset.unavailability_ids)

    def action_view_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Locations',
            'res_model': 'oski.rental.order',
            'view_mode': 'list,form',
            'domain': [('line_ids.asset_id', '=', self.id)],
        }

    def action_view_unavailabilities(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Indisponibilités',
            'res_model': 'oski.rental.unavailability',
            'view_mode': 'list,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id},
        }

    def check_availability(self, date_start, date_end, exclude_line_ids=None):
        """True si aucune ligne réservée/en cours ni indisponibilité ne chevauche
        [date_start, date_end) (bords exclusifs)."""
        self.ensure_one()
        if 'oski.rental.order.line' in self.env:
            domain = [
                ('asset_id', '=', self.id),
                ('state', 'in', ('reserved', 'ongoing')),
                ('date_start', '<', date_end),
                ('date_end', '>', date_start),
            ]
            if exclude_line_ids:
                domain.append(('id', 'not in', exclude_line_ids))
            if self.env['oski.rental.order.line'].search_count(domain):
                return False
        return not self.env['oski.rental.unavailability'].search_count([
            ('asset_id', '=', self.id),
            ('date_start', '<', date_end),
            ('date_end', '>', date_start),
        ])

    def _get_rental_price(self, date_start, date_end):
        """Prix glouton par paliers de durée. Reste arrondi au palier
        le plus fin disponible (+1 unité). Pas d'optimisation meilleur-prix (v1)."""
        self.ensure_one()
        if not date_start or not date_end:
            return 0.0
        seconds = (date_end - date_start).total_seconds()
        if seconds <= 0:
            return 0.0
        granularity = self.env['ir.config_parameter'].sudo().get_param(
            'oski_rental.min_granularity', 'hour')
        tiers = [
            (field_name, duration)
            for field_name, duration in PRICE_TIERS
            if self[field_name] > 0
            and not (granularity == 'day' and field_name == 'price_hour')
        ]
        if not tiers:
            return 0.0
        amount = 0.0
        remaining = seconds
        for field_name, duration in tiers:
            count = int(remaining // duration)
            if count:
                amount += count * self[field_name]
                remaining -= count * duration
        if remaining > 0:
            finest_field = tiers[-1][0]
            amount += self[finest_field]
        return amount
