from odoo import models


class PortalMixin(models.AbstractModel):
    """Toute fiche visible au portail sait dire ce qu'on attend de son client.

    Le greffon se pose sur ``portal.mixin`` et non sur un modèle nommé : le
    devis, la facture, la tâche et tout ce qui viendra plus tard héritent du
    même dépôt sans une ligne de plus.
    """

    _inherit = "portal.mixin"

    def _oski_document_requests(self):
        """Ce que l'on attend du client de CETTE fiche.

        Le visiteur n'entre pas dans le calcul, et ce n'est pas un oubli : le
        portail sert ses pages à partir d'une fiche passée en ``sudo``, si
        bien que ``env.user`` y est le superutilisateur — aussi bien pour un
        client connecté que pour un porteur de lien. Le client de la fiche est
        donc la seule identité fiable à cet endroit, et la page est déjà
        gardée par le jeton ou les droits de lecture.
        """
        self.ensure_one()
        record = self.sudo()
        partner = record.partner_id if "partner_id" in self._fields \
            else self.env["res.partner"]
        return self.env["oski.portal.document.request"]._oski_pending_for(
            record, partner)
