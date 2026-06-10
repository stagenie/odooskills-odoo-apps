# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oski_crm_idle_days = fields.Integer(
        string="Seuil d'inactivité (jours)",
        config_parameter="oski_crm_lead_inactivity.idle_days",
        default=14,
        help="Nombre de jours sans mouvement au-delà duquel une piste ou une "
        "opportunité est considérée comme dormante.",
    )
