from odoo import api, fields, models, tools


class OskiDeleteRule(models.Model):
    """Règle de suppression pour un modèle.

    Une seule règle par modèle : c'est ce qui permet de la retrouver par un
    cache clé/valeur bon marché, appelé à chaque ``unlink`` du serveur.
    """

    _name = "oski.delete.rule"
    _description = "Règle de suppression"
    _order = "model_name"

    model_id = fields.Many2one(
        "ir.model", string="Modèle", required=True, ondelete="cascade",
        help="Modèle dont les suppressions sont surveillées.",
    )
    model_name = fields.Char(related="model_id.model", store=True, string="Nom technique")
    mode = fields.Selection(
        [
            ("block", "Interdire, sauf aux groupes autorisés"),
            ("log", "Autoriser, mais journaliser"),
        ],
        string="Mode", default="block", required=True,
    )
    group_ids = fields.Many2many(
        "res.groups", string="Groupes autorisés",
        help="Utilisateurs qui gardent le droit de supprimer. Laisser vide interdit à tous.",
    )
    message = fields.Char(
        string="Message de refus",
        help="Texte affiché à l'utilisateur bloqué. Laisser vide utilise le message par défaut.",
    )
    active = fields.Boolean(default=True)

    _model_uniq = models.Constraint(
        "UNIQUE (model_id)",
        "Ce modèle a déjà une règle de suppression.",
    )

    @api.model
    @tools.ormcache("model_name")
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
