from odoo import fields, models

# En 20.0, un booléen ``config_parameter`` décoché est stocké « False »
# (``ir.config_parameter.set_bool``) au lieu d'être supprimé : ``default=True``
# vaut donc « activé tant que rien n'a été réglé » et la case reste décochable.


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oski_dup_check_email = fields.Boolean(
        string="Détecter les doublons d'email",
        config_parameter="oski_dup.check_email", default=True,
    )
    oski_dup_check_phone = fields.Boolean(
        string="Détecter les doublons de téléphone",
        config_parameter="oski_dup.check_phone", default=True,
    )
