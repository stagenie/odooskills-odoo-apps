from odoo import models
from odoo.http import request


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _oski_archive_needs_reason(self):
        """Vrai si l'archivage vient du bouton « Archiver » du client web.

        Les appels faits par le code serveur (suppression d'un compte portail,
        désinscription d'un cours, API externe…) attendent un archivage
        immédiat : leur renvoyer l'assistant laisserait le contact actif
        sans erreur.
        """
        if self.env.context.get("oski_archive_confirmed") or not request:
            return False
        httprequest = getattr(request, "httprequest", None)
        path = httprequest.path if httprequest else ""
        return path.endswith(f"/{self._name}/action_archive")

    def action_archive(self):
        """Intercepte l'archivage demandé depuis l'interface pour exiger un motif.

        Une fois le motif confirmé (contexte ``oski_archive_confirmed``), ou
        pour tout appel venant du code serveur, procède à l'archivage standard.
        """
        if not self._oski_archive_needs_reason():
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
