from odoo import _, api, fields, models
from odoo.exceptions import UserError

ZIP_ACTION_CODE = "action = env['ir.attachment']._oski_zip_action(records)"


class IrModel(models.Model):
    """Le téléchargement groupé s'active modèle par modèle.

    Odoo ne permet pas de greffer une entrée de menu sur *tous* les modèles à
    la fois : une action contextuelle vise un modèle. Plutôt que de choisir à
    la place de l'utilisateur une liste de modèles « utiles », le module lui
    laisse cocher les siens, et pose l'action contextuelle correspondante.
    """

    _inherit = "ir.model"

    oski_zip_enabled = fields.Boolean(
        string="Téléchargement groupé",
        help="Ajoute l'entrée « Télécharger les pièces jointes (ZIP) » au menu "
             "d'actions des fiches et des listes de ce modèle.")
    oski_zip_action_id = fields.Many2one(
        "ir.actions.server", string="Action posée", readonly=True,
        ondelete="set null", copy=False)
    oski_zip_available = fields.Boolean(
        string="Peut porter des pièces jointes",
        compute="_compute_oski_zip_available",
        search="_search_oski_zip_available",
        help="Faux pour les modèles abstraits et les assistants : ils n'ont ni "
             "table ni fiche, donc jamais de pièce jointe.")

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
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise UserError(_("Filtre non pris en charge sur ce champ."))
        available = self.sudo().search([]).filtered(
            lambda record: record._oski_zip_is_available()).ids
        wanted = value if operator == "=" else not value
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
                model.sudo().oski_zip_action_id = self.env[
                    "ir.actions.server"].sudo().create(model._oski_zip_values())
            elif not wanted and action:
                # ondelete='set null' remet le champ à vide de lui-même.
                action.unlink()

    def _oski_zip_values(self):
        self.ensure_one()
        return {
            "name": _("Télécharger les pièces jointes (ZIP)"),
            "model_id": self.id,
            "binding_model_id": self.id,
            "binding_type": "action",
            "binding_view_types": "list,form",
            "state": "code",
            "code": ZIP_ACTION_CODE,
        }
