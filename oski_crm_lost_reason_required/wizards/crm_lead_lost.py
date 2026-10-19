from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.mail import is_html_empty


class CrmLeadLost(models.TransientModel):
    """L'assistant apprend l'exigence, l'écran la montre.

    Rendre le champ obligatoire à l'écran ne suffirait pas — un appel direct
    contournerait la règle — mais l'omettre condamnerait l'utilisateur à
    découvrir le refus après coup, une fois le formulaire rempli.
    """

    _inherit = "crm.lead.lost"

    oski_reason_required = fields.Boolean(
        string="Motif obligatoire", compute="_compute_oski_required")
    oski_feedback_required = fields.Boolean(
        string="Note obligatoire", compute="_compute_oski_required")

    @api.depends("lead_ids")
    def _compute_oski_required(self):
        for wizard in self:
            companies = wizard.lead_ids.company_id or self.env.company
            wizard.oski_reason_required = any(
                company.oski_lost_reason_required for company in companies)
            wizard.oski_feedback_required = any(
                company.oski_lost_feedback_required for company in companies)

    def action_lost_reason_apply(self):
        if self.oski_feedback_required and is_html_empty(self.lost_feedback):
            raise UserError(_(
                "Quelques mots de contexte sont attendus en plus du motif : "
                "c'est ce que relira celui qui reprendra ce client dans un an."))
        return super().action_lost_reason_apply()
