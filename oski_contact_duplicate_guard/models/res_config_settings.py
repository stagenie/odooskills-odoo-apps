from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oski_dup_check_email = fields.Boolean(
        string="Détecter les doublons d'email",
        config_parameter="oski_dup.check_email",
        default=True,
    )
    oski_dup_check_phone = fields.Boolean(
        string="Détecter les doublons de téléphone",
        config_parameter="oski_dup.check_phone",
        default=True,
    )
