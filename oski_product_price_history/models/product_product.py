from odoo import models


class ProductProduct(models.Model):
    """Le coût se tient par variante ET par société.

    ``standard_price`` est un champ dépendant de la société : deux filiales
    peuvent valoriser le même article différemment, et l'historique doit dire
    laquelle a bougé.
    """

    _inherit = "product.product"

    def write(self, vals):
        if "standard_price" not in vals:
            return super().write(vals)
        previous = {product.id: product.standard_price for product in self}
        result = super().write(vals)
        self.env["oski.product.price.history"]._oski_track(
            self, "standard_price", previous)
        return result
