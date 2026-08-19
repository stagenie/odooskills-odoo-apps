from odoo import api, fields, models

FIELDS = [
    ("list_price", "Prix de vente"),
    ("standard_price", "Coût"),
]


class OskiProductPriceHistory(models.Model):
    """Une ligne par changement de prix, et rien d'autre.

    Aucune purge automatique n'est prévue, contrairement aux journaux
    techniques de la gamme : un historique de prix qui s'efface au bout de
    trente jours ne répond plus à la seule question qu'on lui pose — quand
    avons-nous augmenté, et de combien ?
    """

    _name = "oski.product.price.history"
    _description = "Historique des prix"
    _order = "changed_on desc, id desc"
    _rec_name = "product_tmpl_id"

    product_tmpl_id = fields.Many2one(
        "product.template", string="Article", required=True, index=True,
        ondelete="cascade")
    product_id = fields.Many2one(
        "product.product", string="Variante", index=True, ondelete="cascade",
        help="Renseignée pour le coût, qui se tient par variante.")
    field_name = fields.Selection(FIELDS, string="Prix", required=True, index=True)
    old_value = fields.Float(string="Avant", digits="Product Price", readonly=True)
    new_value = fields.Float(string="Après", digits="Product Price", readonly=True)
    variation = fields.Float(
        string="Écart", digits="Product Price", compute="_compute_variation",
        store=True)
    variation_percent = fields.Float(
        string="Écart (%)", digits=(5, 2), compute="_compute_variation", store=True)
    changed_on = fields.Datetime(
        string="Le", required=True, index=True, default=fields.Datetime.now)
    user_id = fields.Many2one(
        "res.users", string="Par", default=lambda self: self.env.user,
        ondelete="set null")
    company_id = fields.Many2one(
        "res.company", string="Société", required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", readonly=True)

    @api.depends("old_value", "new_value")
    def _compute_variation(self):
        for record in self:
            record.variation = record.new_value - record.old_value
            record.variation_percent = (
                100.0 * record.variation / record.old_value
                if record.old_value else 0.0)

    @api.model
    def _oski_track(self, records, field_name, previous):
        """Écrit les lignes pour les enregistrements dont le prix a bougé.

        ``previous`` porte les valeurs relevées AVANT l'écriture : elles ne
        sont plus lisibles après, et c'est tout l'objet de l'historique.
        """
        rows = []
        for record in records:
            before = previous.get(record.id)
            after = record[field_name]
            if before is None or float(before) == float(after):
                continue
            rows.append({
                "product_tmpl_id": (
                    record.product_tmpl_id.id
                    if record._name == "product.product" else record.id),
                "product_id": (
                    record.id if record._name == "product.product" else False),
                "field_name": field_name,
                "old_value": before,
                "new_value": after,
            })
        return self.sudo().create(rows) if rows else self.browse()
