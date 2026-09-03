from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    oski_price_history_ids = fields.One2many(
        "oski.product.price.history", "product_tmpl_id", string="Historique des prix")
    oski_price_history_count = fields.Integer(
        string="Changements de prix", compute="_compute_oski_price_history_count")

    def _compute_oski_price_history_count(self):
        counts = {
            template.id: count
            for template, count in self.env["oski.product.price.history"]._read_group(
                [("product_tmpl_id", "in", self.ids)],
                ["product_tmpl_id"], ["__count"])}
        for template in self:
            template.oski_price_history_count = counts.get(template.id, 0)

    def write(self, vals):
        if "list_price" not in vals:
            return super().write(vals)
        # Le relevé se prend AVANT l'écriture : après, l'ancienne valeur
        # n'existe plus nulle part.
        previous = {template.id: template.list_price for template in self}
        result = super().write(vals)
        self.env["oski.product.price.history"]._oski_track(
            self, "list_price", previous)
        return result

    def action_oski_price_history(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Historique des prix"),
            "res_model": "oski.product.price.history",
            "view_mode": "list,graph",
            "domain": [("product_tmpl_id", "=", self.id)],
            "context": {"create": False},
        }
