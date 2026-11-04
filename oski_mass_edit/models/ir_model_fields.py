from odoo import api, models


class IrModelFields(models.Model):
    """Recherche des champs pour l'assistant d'édition en masse.

    ``ir.model.fields`` n'est lisible que par les administrateurs ; un utilisateur
    interne ne pourrait donc pas choisir le champ à modifier. Sous la clé de contexte
    ``oski_mass_edit_model`` (posée par la vue de l'assistant), la recherche est
    déléguée en ``sudo`` mais restreinte aux champs du modèle désigné, et seulement
    si l'utilisateur a le droit d'écrire ce modèle — l'écriture finale, elle, reste
    soumise à ses droits (voir ``OskiMassEditWizard.action_apply``).
    """
    _inherit = "ir.model.fields"

    def _oski_mass_edit_domain(self):
        """Domaine imposé sous la clé de contexte, ou ``None`` hors assistant."""
        model_name = self.env.context.get("oski_mass_edit_model")
        if not model_name or self.env.su:
            return None
        target = self.env.get(model_name)
        if target is None or target._transient or not target.has_access("write"):
            return False
        return [("model", "=", model_name)]

    def _oski_mass_edit_sudo(self):
        return self.sudo().with_context(oski_mass_edit_model=False)

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        forced = self._oski_mass_edit_domain()
        if forced is None:
            return super().name_search(name, domain, operator, limit)
        if forced is False:
            return []
        return self._oski_mass_edit_sudo().name_search(name, list(domain or []) + forced, operator, limit)

    @api.model
    def web_name_search(self, name, specification, domain=None, operator="ilike", limit=100):
        forced = self._oski_mass_edit_domain()
        if forced is None:
            return super().web_name_search(name, specification, domain, operator, limit)
        if forced is False:
            return []
        return self._oski_mass_edit_sudo().web_name_search(
            name, specification, list(domain or []) + forced, operator, limit)
