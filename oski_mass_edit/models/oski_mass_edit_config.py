from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OskiMassEditConfig(models.Model):
    """Déclare les modèles sur lesquels l'édition en masse est proposée.

    Chaque configuration pilote une ``ir.actions.act_window`` liée au modèle
    (``binding_model_id``) : c'est elle qui fait apparaître l'entrée dans le
    menu « Actions » de la vue liste. Le module ne touche à aucune vue.
    """

    _name = "oski.mass.edit.config"
    _description = "Modèle ouvert à l'édition en masse"
    _order = "model_name"

    model_id = fields.Many2one(
        "ir.model", string="Modèle", required=True, ondelete="cascade",
        help="Modèle dont la vue liste proposera l'édition en masse.",
    )
    model_name = fields.Char(related="model_id.model", store=True, string="Nom technique")
    active = fields.Boolean(default=True)
    action_id = fields.Many2one(
        "ir.actions.act_window", string="Action générée", readonly=True,
        ondelete="set null",
    )

    _model_uniq = models.Constraint(
        "UNIQUE (model_id)",
        "Ce modèle est déjà ouvert à l'édition en masse.",
    )

    def _action_vals(self):
        self.ensure_one()
        return {
            "name": _("Édition en masse"),
            "res_model": "oski.mass.edit.wizard",
            "binding_model_id": self.model_id.id,
            "binding_view_types": "list",
            "view_mode": "form",
            "target": "new",
        }

    def _sync_action(self):
        for config in self:
            if not config.active:
                # Retirer la liaison suffit : l'entrée disparaît du menu Actions
                # sans détruire l'action, donc sans perdre la configuration.
                if config.action_id:
                    config.action_id.binding_model_id = False
                continue
            vals = config._action_vals()
            if config.action_id:
                config.action_id.write(vals)
            else:
                config.action_id = self.env["ir.actions.act_window"].create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        configs = super().create(vals_list)
        configs._sync_action()
        return configs

    def write(self, vals):
        res = super().write(vals)
        if {"model_id", "active"} & set(vals):
            self._sync_action()
        return res

    def unlink(self):
        self.action_id.unlink()
        return super().unlink()

    @api.constrains("model_id")
    def _check_model_is_editable(self):
        for config in self:
            model = self.env.get(config.model_name)
            if model is None:
                raise UserError(
                    _("Le modèle « %s » n'existe pas dans ce serveur.", config.model_name)
                )
            if model._abstract or model._transient:
                raise UserError(
                    _("« %s » est un modèle abstrait ou transitoire : il n'a pas de "
                      "vue liste durable à équiper.", config.model_name)
                )
