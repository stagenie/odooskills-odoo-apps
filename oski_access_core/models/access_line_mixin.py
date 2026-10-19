# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class OskiAccessLineMixin(models.AbstractModel):
    _name = "oski.access.line.mixin"
    _description = "Ligne d'accès Oski (abstrait)"

    level = fields.Selection(
        selection=[("read", "Lecture seule"), ("full", "Complet")],
        string="Niveau",
        required=True,
        default="full",
    )
    user_id = fields.Many2one("res.users", string="Utilisateur", ondelete="cascade")
    group_id = fields.Many2one("res.groups", string="Groupe", ondelete="cascade")

    @api.constrains("user_id", "group_id", "level")
    def _check_user_xor_group(self):
        for line in self:
            if bool(line.user_id) == bool(line.group_id):
                raise ValidationError(
                    "Renseignez soit un utilisateur, soit un groupe "
                    "(exactement l'un des deux)."
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._oski_access_changed()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._oski_access_changed()
        return res

    def unlink(self):
        res = super().unlink()
        self._oski_access_changed()
        return res

    def _oski_access_changed(self):
        """Les domaines des ir.rule sont en ormcache par utilisateur : sans purge,
        une ligne ajoutée, modifiée ou retirée ne s'applique qu'au redémarrage.
        Les modules concrets peuvent étendre (champs calculés à invalider)."""
        self.env.registry.clear_cache()

    def _resolve_levels(self, user, dimension_field):
        """Agrège les lignes personnelles (user_id) et de groupe (group_id dans
        les groupes de `user`). Renvoie (read, full) recordsets de la dimension :
        read = read ∪ full ; full = dimensions ayant au moins une ligne 'full'.
        Le niveau maximum gagne. À appeler sur le modèle concret héritant du mixin."""
        lines = self.search([
            "|",
            ("user_id", "=", user.id),
            ("group_id", "in", user.groups_id.ids),
        ])
        full = lines.filtered(lambda l: l.level == "full").mapped(dimension_field)
        read = lines.mapped(dimension_field)
        return read, full
