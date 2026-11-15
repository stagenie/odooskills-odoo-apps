from odoo import api, fields, models, tools


class OskiAuditRule(models.Model):
    """Ce qu'il faut surveiller, et sur quel modèle."""

    _name = "oski.audit.rule"
    _description = "Logging Rule"
    _order = "model_name"

    model_id = fields.Many2one(
        "ir.model", string="Model", required=True, ondelete="cascade",
    )
    model_name = fields.Char(related="model_id.model", store=True, string="Technical Name")
    log_create = fields.Boolean(string="Creations", default=True)
    log_write = fields.Boolean(string="Updates", default=True)
    log_unlink = fields.Boolean(string="Deletions", default=True)
    field_ids = fields.Many2many(
        "ir.model.fields", string="Watched Fields",
        domain="[('model_id', '=', model_id)]",
        help="Restricts update logging to these fields. Leave empty to "
             "watch all stored fields.",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("model_uniq", "UNIQUE (model_id)", "This model already has a logging rule."),
    ]

    @api.model
    @tools.ormcache("model_name")
    def _rule_for_model(self, model_name):
        """Règle applicable, en tuple immuable — jamais un recordset.

        Cette méthode est consultée à chaque création, écriture et suppression
        du serveur : elle doit coûter le prix d'une lecture de dictionnaire.
        """
        rule = self.sudo().search([("model_name", "=", model_name)], limit=1)
        if not rule:
            return None
        return (
            rule.log_create,
            rule.log_write,
            rule.log_unlink,
            tuple(rule.field_ids.mapped("name")),
        )

    def _invalidate_rule_cache(self):
        self.env.registry.clear_cache()

    @api.model_create_multi
    def create(self, vals_list):
        rules = super().create(vals_list)
        rules._invalidate_rule_cache()
        return rules

    def write(self, vals):
        res = super().write(vals)
        self._invalidate_rule_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self._invalidate_rule_cache()
        return res
