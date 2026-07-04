from datetime import timedelta

from odoo import api, fields, models


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

    def check_availability(self, date_start, date_end, exclude_line_ids=None):
        """True si aucune ligne réservée/en cours ni indisponibilité ne chevauche."""
        self.ensure_one()
        # Implémentation complétée en Task 4 (dépend de order.line et unavailability).
        return True
