from odoo import _, models
from odoo.exceptions import UserError

# Modèles jamais surveillés : le journal lui-même (sinon purger le journal
# déclencherait de nouvelles écritures dans le journal) et sa configuration.
UNGUARDED = ("oski.delete.log", "oski.delete.rule")


class Base(models.AbstractModel):
    """Greffe le garde-fou sur ``unlink`` de tous les modèles du serveur."""

    _inherit = "base"

    def _oski_delete_rule(self):
        if self._transient or self._abstract or self._name in UNGUARDED:
            return None
        return self.env["oski.delete.rule"]._rule_for_model(self._name)

    def _oski_check_delete_allowed(self, rule):
        mode, group_ids, message = rule
        if mode != "block":
            return
        user_groups = set(self.env.user._get_group_ids())
        if user_groups & set(group_ids):
            return
        raise UserError(
            message
            or _("La suppression est interdite sur « %s ». Demandez-la à un utilisateur habilité.",
                 self.env["ir.model"]._get(self._name).name or self._name)
        )

    def _oski_log_deletion(self):
        """Inscrit les enregistrements au journal avant leur disparition.

        L'écriture précède le ``super()`` parce qu'après lui, ni l'identifiant
        ni le nom affiché ne sont plus lisibles. Elle partage la transaction de
        la suppression : si celle-ci échoue, la trace disparaît avec elle.
        """
        label = self.env["ir.model"]._get(self._name).name
        self.env["oski.delete.log"].sudo().create([
            {
                "model_name": self._name,
                "model_label": label,
                "res_id": record.id,
                "res_name": record.display_name,
                "user_id": self.env.uid,
            }
            for record in self
        ])

    def unlink(self):
        # Les opérations menées en superutilisateur — installation, mise à
        # jour, désinstallation, tâches planifiées — traversent le garde-fou
        # sans être arrêtées : il protège l'interface, pas la maintenance.
        if self and not self.env.su:
            rule = self._oski_delete_rule()
            if rule:
                self._oski_check_delete_allowed(rule)
                self._oski_log_deletion()
        return super().unlink()
