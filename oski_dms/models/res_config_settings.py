from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Réglages GED : espace de classement par défaut et plafond de taille upload."""

    _inherit = 'res.config.settings'

    dms_default_workspace_id = fields.Many2one(
        'oski.dms.workspace', string="Espace par défaut",
        config_parameter='oski_dms.default_workspace_id')
    dms_max_upload_mb = fields.Integer(
        string="Taille max upload (Mo)", default=25,
        config_parameter='oski_dms.max_upload_mb')
