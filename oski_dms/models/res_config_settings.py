from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Réglages GED : espace de classement par défaut et plafond de taille upload."""

    _inherit = 'res.config.settings'

    dms_default_workspace_id = fields.Many2one(
        'oski.dms.workspace', string="Espace par défaut",
        config_parameter='oski_dms.default_workspace_id')
    dms_max_upload_mb = fields.Integer(
        # Pas de `default` : 0 (paramètre absent) = illimité, ce qu'applique
        # `_inverse_file`. Un default=25 affichait 25 Mo sans les appliquer,
        # et rendait « 0 = illimité » impossible à saisir (0 efface le
        # paramètre, l'écran réaffichait 25).
        string="Taille max upload (Mo)",
        config_parameter='oski_dms.max_upload_mb')
