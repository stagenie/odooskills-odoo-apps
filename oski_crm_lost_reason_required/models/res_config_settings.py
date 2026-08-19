from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oski_lost_reason_required = fields.Boolean(
        related="company_id.oski_lost_reason_required", readonly=False)
    oski_lost_feedback_required = fields.Boolean(
        related="company_id.oski_lost_feedback_required", readonly=False)
