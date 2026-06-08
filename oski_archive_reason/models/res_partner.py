from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_archive(self):
        """Intercepte l'archivage pour exiger un motif.

        Si l'archivage n'a pas encore été confirmé via le wizard, ouvre la
        fenêtre de saisie du motif. Une fois confirmé (contexte
        ``oski_archive_confirmed``), procède à l'archivage standard.
        """
        if self.env.context.get("oski_archive_confirmed"):
            return super().action_archive()
        return {
            "type": "ir.actions.act_window",
            "name": "Motif d'archivage",
            "res_model": "oski.archive.reason.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "active_model": self._name,
                "active_ids": self.ids,
            },
        }
