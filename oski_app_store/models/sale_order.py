from odoo import api, fields, models


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
