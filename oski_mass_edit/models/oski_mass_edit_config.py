from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OskiMassEditConfig(models.Model):
    """Déclare les modèles sur lesquels l'édition en masse est proposée.

    Chaque configuration pilote une ``ir.actions.act_window`` liée au modèle
    (``binding_model_id``) : c'est elle qui fait apparaître l'entrée dans le
    menu « Actions » de la vue liste. Le module ne touche à aucune vue.
    """

    _name = "oski.mass.edit.config"
    _description = "Mass Edit Model"
    _order = "model_name"

    model_id = fields.Many2one(
        "ir.model", string="Model", required=True, ondelete="cascade",
        help="Model whose list view will offer mass editing.",
    )
    model_name = fields.Char(related="model_id.model", store=True, string="Technical Name")
    active = fields.Boolean(default=True)
    action_id = fields.Many2one(
        "ir.actions.act_window", string="Generated Action", readonly=True,
        ondelete="set null",
    )

    _model_uniq = models.Constraint(
        "UNIQUE (model_id)",
        "This model is already open to mass editing.",
    )

    def _action_vals(self):
        self.ensure_one()
        return {
            "name": _("Mass Edit"),
            "res_model": "oski.mass.edit.wizard",
            "binding_model_id": self.model_id.id,
            "binding_view_types": "list",
            "view_mode": "form",
            "target": "new",
        }

    def _action_name_translations(self):
        """Le libellé de l'entrée du menu Actions dans chaque langue installée.

        en_US toujours compris : en 20, quand en_US n'est pas active, écrire
        une autre langue recopie sa valeur dans en_US (``fields_textual.py``).
        """
        self.ensure_one()
        codes = {code for code, _label in self.env["res.lang"].get_installed()}
        return {
            code: self.with_context(lang=code)._action_vals()["name"]
            for code in codes | {"en_US"}}

    def _sync_action(self):
        for config in self:
            if not config.active:
                # Retirer la liaison suffit : l'entrée disparaît du menu Actions
                # sans détruire l'action, donc sans perdre la configuration.
                if config.action_id:
                    config.action_id.binding_model_id = False
                continue
            # Écrite en en_US (la source), puis traduite dans chaque langue
            # installée : le libellé du menu Actions ne dépend pas de la
            # langue de qui enregistre la configuration.
            vals = config.with_context(lang="en_US")._action_vals()
            if config.action_id:
                config.action_id.with_context(lang="en_US").write(vals)
            else:
                config.action_id = self.env["ir.actions.act_window"].with_context(
                    lang="en_US").create(vals)
            config.action_id.update_field_translations(
                "name", config._action_name_translations())

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
                raise ValidationError(
                    _("Model “%s” does not exist on this server.", config.model_name)
                )
            if model._abstract or model._transient:
                raise ValidationError(
                    _("“%s” is an abstract or transient model: it has no lasting "
                      "list view to equip.", config.model_name)
                )
