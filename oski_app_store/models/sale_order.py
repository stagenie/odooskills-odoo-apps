from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Pays du client de la commande d'achat : stocké pour grouper et filtrer
    # les ventes du store par pays dans les vues liste et pivot.
    oski_country_id = fields.Many2one(
        "res.country",
        string="Customer country",
        related="partner_id.country_id",
        store=True,
        readonly=True,
    )
