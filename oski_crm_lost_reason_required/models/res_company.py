from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    oski_lost_reason_required = fields.Boolean(
        string="Mandatory Lost Reason", default=True,
        help="Forbids losing an opportunity without saying why.")
    oski_lost_feedback_required = fields.Boolean(
        string="Mandatory Closing Note", default=False,
        help="Also requires a few words of context, beyond the reason picked "
             "from the list.")
