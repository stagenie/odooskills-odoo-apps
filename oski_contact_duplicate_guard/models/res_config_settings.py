from odoo import api, fields, models

# Paramètres stockés en toutes lettres « True » / « False » : un booléen déclaré
# avec ``config_parameter`` et ``default=True`` ne peut pas être décoché (décocher
# supprime le paramètre, et l'absence de paramètre vaut « activé »).
OSKI_DUP_PARAMS = {
    "oski_dup_check_email": "oski_dup.check_email",
    "oski_dup_check_phone": "oski_dup.check_phone",
}


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oski_dup_check_email = fields.Boolean(string="Détecter les doublons d'email")
    oski_dup_check_phone = fields.Boolean(string="Détecter les doublons de téléphone")

    @api.model
    def get_values(self):
        res = super().get_values()
        icp = self.env["ir.config_parameter"].sudo()
        for fname, key in OSKI_DUP_PARAMS.items():
            res[fname] = icp.get_param(key, "True") not in ("False", "false", "0", "")
        return res

    def set_values(self):
        super().set_values()
        icp = self.env["ir.config_parameter"].sudo()
        for fname, key in OSKI_DUP_PARAMS.items():
            icp.set_param(key, "True" if self[fname] else "False")
