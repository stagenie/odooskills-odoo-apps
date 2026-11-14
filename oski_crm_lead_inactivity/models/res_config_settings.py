# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oski_crm_idle_days = fields.Integer(
        string="Idle Threshold (Days)",
        config_parameter="oski_crm_lead_inactivity.idle_days",
        default=14,
        help="Number of days without movement after which a lead or an "
        "opportunity is considered idle.",
    )
