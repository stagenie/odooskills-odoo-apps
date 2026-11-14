from odoo import _, api, fields, models

ZIP_ACTION_CODE = "action = env['ir.attachment']._oski_zip_action(records)"

def oski_wanted(operator, value):
    """Traduit une condition booléenne en « on cherche les vrais » ou non.

    Odoo 19 NORMALISE ``('champ', '=', True)`` en ``operator='in'`` et
    ``value=OrderedSet([True])`` avant d'appeler la méthode ``search`` d'un
    champ. Lire l'opérateur brut rendrait alors le complément exact du
    résultat attendu — une liste qui a l'air plausible et qui est fausse.
    """
    if operator in ("in", "not in"):
        truthy = any(bool(item) for item in value)
        return truthy if operator == "in" else not truthy
    if operator in ("=", "!="):
        return bool(value) if operator == "=" else not bool(value)
    raise NotImplementedError(
        "Unsupported operator on this field: %s" % operator)



class IrModel(models.Model):
    """Le téléchargement groupé s'active modèle par modèle.

    Odoo ne permet pas de greffer une entrée de menu sur *tous* les modèles à
    la fois : une action contextuelle vise un modèle. Plutôt que de choisir à
    la place de l'utilisateur une liste de modèles « utiles », le module lui
    laisse cocher les siens, et pose l'action contextuelle correspondante.
    """

    _inherit = "ir.model"

    oski_zip_enabled = fields.Boolean(
        string="Bulk Download",
        help="Adds the “Download attachments (ZIP)” entry to the Actions menu "
             "of this model's records and lists.")
    oski_zip_action_id = fields.Many2one(
        "ir.actions.server", string="Created Action", readonly=True,
        ondelete="set null", copy=False)
    oski_zip_available = fields.Boolean(
        string="Can Hold Attachments",
        compute="_compute_oski_zip_available",
        search="_search_oski_zip_available",
        help="False for abstract models and wizards: they have neither table "
             "nor record, hence never any attachment.")

    def _oski_zip_is_available(self):
        """Un modèle abstrait — ``mail.thread``, un mixin — n'a pas de fiche.

        Le proposer dans l'écran de configuration promettrait une entrée de
        menu qui ne s'afficherait jamais.
        """
        self.ensure_one()
        model = self.env.get(self.model)
        # ``model`` est un recordset VIDE quand le modèle existe : le tester
        # en booléen le déclarerait absent à tous les coups.
        return model is not None and not model._abstract and not model._transient

    def _compute_oski_zip_available(self):
        for record in self:
            record.oski_zip_available = record._oski_zip_is_available()

    def _search_oski_zip_available(self, operator, value):
        """Le champ n'est pas stocké, et c'est voulu : la liste des modèles
        change à chaque module installé, une valeur en base vieillirait sans
        que rien ne la rafraîchisse."""
        wanted = oski_wanted(operator, value)
        available = self.sudo().search([]).filtered(
            lambda record: record._oski_zip_is_available()).ids
        return [("id", "in" if wanted else "not in", available)]

    @api.model_create_multi
    def create(self, vals_list):
        models_ = super().create(vals_list)
        models_._oski_sync_zip_action()
        return models_

    def write(self, vals):
        result = super().write(vals)
        if "oski_zip_enabled" in vals:
            self._oski_sync_zip_action()
        return result

    def _oski_sync_zip_action(self):
        """Aligne l'action contextuelle sur la case cochée.

        Appelée après coup et jamais depuis un calcul : l'action est une
        donnée, pas un cache, et doit survivre à une mise à jour du module.
        """
        for model in self:
            wanted = model.oski_zip_enabled and model.oski_zip_available
            action = model.oski_zip_action_id.sudo()
            if wanted and not action:
                # Créée en en_US (la source), puis traduite dans chaque langue
                # installée : le libellé du menu Action ne dépend pas de la
                # langue de qui a coché la case.
                action = self.env["ir.actions.server"].sudo().with_context(
                    lang="en_US").create(model.with_context(lang="en_US")._oski_zip_values())
                action.update_field_translations(
                    "name", model._oski_zip_name_translations())
                model.sudo().oski_zip_action_id = action
            elif not wanted and action:
                # ondelete='set null' remet le champ à vide de lui-même.
                action.unlink()

    def _oski_zip_name_translations(self):
        """Le libellé de l'entrée de menu dans chaque langue installée.

        en_US toujours compris : en 20, quand en_US n'est pas active, écrire
        une autre langue recopie sa valeur dans en_US (``fields_textual.py``).
        """
        codes = {code for code, _label in self.env["res.lang"].get_installed()}
        return {
            code: self.with_context(lang=code)._oski_zip_values()["name"]
            for code in codes | {"en_US"}}

    def _oski_zip_values(self):
        self.ensure_one()
        return {
            "name": _("Download attachments (ZIP)"),
            "model_id": self.id,
            "binding_model_id": self.id,
            "binding_type": "action",
            "binding_view_types": "list,form",
            "state": "code",
            "code": ZIP_ACTION_CODE,
        }
