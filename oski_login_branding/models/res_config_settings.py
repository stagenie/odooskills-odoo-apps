from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oski_login_bg_color = fields.Char(
        string="Login Background Color",
        config_parameter="oski_login.bg_color",
    )
    oski_login_accent_color = fields.Char(
        string="Login Accent Color",
        config_parameter="oski_login.accent_color",
    )
