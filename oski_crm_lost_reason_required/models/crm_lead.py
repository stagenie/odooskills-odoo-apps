from odoo import _, models
from odoo.exceptions import UserError


class CrmLead(models.Model):
    """L'exigence se pose sur le modèle, pas seulement sur l'assistant.

    Perdre une opportunité passe aussi par un import, une action serveur ou un
    appel direct : une règle qui ne vivrait que dans l'écran laisserait toutes
    ces portes ouvertes.
    """

    _inherit = "crm.lead"

    def action_set_lost(self, **additional_values):
        self._oski_check_lost_reason(additional_values)
        return super().action_set_lost(**additional_values)

    def _oski_check_lost_reason(self, values=None):
        values = values or {}
        nameless = self.env["crm.lead"]
        for lead in self:
            company = lead.company_id or self.env.company
            if not company.oski_lost_reason_required:
                continue
            if not (values.get("lost_reason_id") or lead.lost_reason_id):
                nameless |= lead
        if nameless:
            raise UserError(_(
                "Ces opportunités ne peuvent pas être perdues sans motif :\n%s",
                "\n".join("• %s" % lead.display_name for lead in nameless)))
