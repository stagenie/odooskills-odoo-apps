from odoo import api, fields, models


class OskiDeleteRule(models.Model):
    """Règle de suppression pour un modèle.

    Une seule règle par modèle : c'est ce qui permet de la retrouver par un
    cache clé/valeur bon marché, appelé à chaque ``unlink`` du serveur.
    """

    _name = "oski.delete.rule"
    _description = "Deletion Rule"
    _order = "model_name"
    # Sans nom affichable, le fil d'Ariane de la fiche montrait « oski.delete.rule,2 ».
    _rec_name = "model_id"

    model_id = fields.Many2one(
        "ir.model", string="Model", required=True, ondelete="cascade",
        domain=[("transient", "=", False)],
        help="Model whose deletions are watched.",
    )
    model_name = fields.Char(related="model_id.model", store=True, string="Technical Name")
    mode = fields.Selection(
        [
            ("block", "Block, except for allowed groups"),
            ("log", "Allow, but log"),
        ],
        string="Mode", default="block", required=True,
    )
    group_ids = fields.Many2many(
        "res.groups", string="Allowed Groups",
        help="Users who keep the right to delete. Leave empty to block everyone.",
    )
    message = fields.Char(
        string="Refusal Message",
        help="Text shown to the blocked user. Leave empty to use the default message.",
    )
    active = fields.Boolean(default=True)

    _model_uniq = models.Constraint(
        "UNIQUE (model_id)",
        "This model already has a deletion rule.",
    )

    @api.model
    @api.ormcache("model_name")
    def _rule_for_model(self, model_name):
        """Règle applicable à un modèle, sous forme de tuple immuable.

        Le retour ne contient aucun recordset : un cache ORM qui mémoriserait
        des enregistrements les servirait à des environnements auxquels ils
        n'appartiennent pas.
        """
        rule = self.sudo().search([("model_name", "=", model_name)], limit=1)
        if not rule:
            return None
        return (rule.mode, tuple(rule.group_ids.ids), rule.message or "")

    def _invalidate_rule_cache(self):
        # Les règles sont lues à chaque suppression du serveur : elles vivent
        # dans le cache du registre, qu'il faut vider dès qu'elles changent.
        self.env.transaction.invalidate_ormcache()

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
