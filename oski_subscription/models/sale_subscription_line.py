from odoo import api, fields, models


class SaleSubscriptionLine(models.Model):
    _name = "sale.subscription.line"
    _description = "Ligne d'abonnement"
    _check_company_auto = True

    subscription_id = fields.Many2one(
        "sale.subscription", string="Abonnement", required=True, ondelete="cascade"
    )
    company_id = fields.Many2one(
        related="subscription_id.company_id", string="Société", store=True
    )
    product_id = fields.Many2one(
        "product.product", string="Produit", required=True, check_company=True
    )
    name = fields.Char(string="Description")
    quantity = fields.Float(string="Quantité", default=1.0)
    price_unit = fields.Float(string="Prix unitaire")
    discount = fields.Float(string="Remise (%)", default=0.0)
    tax_ids = fields.Many2many("account.tax", string="Taxes", check_company=True)
    currency_id = fields.Many2one(
        related="subscription_id.currency_id", string="Devise"
    )
    price_subtotal = fields.Monetary(
        string="Sous-total", compute="_compute_price_subtotal", store=True
    )

    @api.depends("quantity", "price_unit", "discount")
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = (
                line.quantity * line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)
            )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id:
                continue
            line.name = line.product_id.display_name
            line.price_unit = line.product_id.list_price
            # taxes du produit limitées à la société de l'abonnement
            line.tax_ids = line.product_id.taxes_id._filter_taxes_by_company(
                line.company_id or self.env.company
            )
