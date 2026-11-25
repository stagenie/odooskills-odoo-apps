from datetime import timedelta

from odoo import api, fields, models

# Un panier anonyme jamais transformé en commande est jeté après ce délai.
ANONYMOUS_CART_TTL_DAYS = 3
ANONYMOUS_CART_BATCH = 2000


class SaleOrder(models.Model):
    _inherit = "sale.order"

    oski_geo_country_id = fields.Many2one(
        "res.country",
        string="Visitor country (geolocation)",
        readonly=True,
        copy=False,
        help="Country of the visitor who clicked Buy, from geolocation. "
             "No IP address is stored.",
    )
    oski_country_id = fields.Many2one(
        "res.country",
        string="Customer country",
        compute="_compute_oski_country_id",
        store=True,
        readonly=True,
        help="Customer's country when known, otherwise the country of the "
             "visitor who clicked Buy.",
    )

    @api.depends("partner_id.country_id", "oski_geo_country_id")
    def _compute_oski_country_id(self):
        public = self.env.ref("base.public_partner", raise_if_not_found=False)
        for order in self:
            partner_country = order.partner_id != public and order.partner_id.country_id
            order.oski_country_id = partner_country or order.oski_geo_country_id

    @api.model
    def _oski_anonymous_cart_domain(self, days=ANONYMOUS_CART_TTL_DAYS):
        """Paniers du site restés au nom du visiteur anonyme, sans paiement.

        Un vrai acheteur saisit son adresse au passage en caisse : le devis
        change alors de client. Ce qui reste au nom de « Public user » est un
        panier abandonné, le plus souvent ouvert par un robot.
        """
        websites = self.env["website"].sudo().search([])
        public = websites.user_id.partner_id | self.env.ref("base.public_partner")
        return [
            ("state", "=", "draft"),
            ("website_id", "!=", False),
            ("partner_id", "in", public.ids),
            ("transaction_ids", "=", False),
            ("create_date", "<", fields.Datetime.now() - timedelta(days=days)),
        ]

    @api.model
    def _cron_oski_purge_anonymous_carts(self, days=ANONYMOUS_CART_TTL_DAYS, limit=ANONYMOUS_CART_BATCH):
        """Supprime les paniers anonymes abandonnés depuis plus de `days` jours."""
        carts = self.sudo().search(self._oski_anonymous_cart_domain(days), limit=limit)
        count = len(carts)
        carts.unlink()
        return count
