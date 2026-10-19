from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oski_timesheet_reminder_active = fields.Boolean(
        related="company_id.oski_timesheet_reminder_active", readonly=False)
    oski_timesheet_expected_hours = fields.Float(
        related="company_id.oski_timesheet_expected_hours", readonly=False)
    oski_timesheet_tolerance = fields.Float(
        related="company_id.oski_timesheet_tolerance", readonly=False)
