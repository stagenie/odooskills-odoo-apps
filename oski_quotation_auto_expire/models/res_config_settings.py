from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oski_quote_expire_active = fields.Boolean(
        related="company_id.oski_quote_expire_active", readonly=False)
    oski_quote_reminder_days = fields.Integer(
        related="company_id.oski_quote_reminder_days", readonly=False)
