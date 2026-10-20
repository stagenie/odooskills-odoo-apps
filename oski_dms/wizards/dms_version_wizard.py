from odoo import fields, models


class DmsVersionWizard(models.TransientModel):
    _name = 'oski.dms.version.wizard'
    _description = "Nouvelle version de document"

    document_id = fields.Many2one('oski.dms.document', string="Document", required=True)
    file = fields.Binary(string="Nouveau fichier", required=True)
    file_name = fields.Char(string="Nom du fichier")

    def action_create_version(self):
        """Crée la nouvelle version via `action_new_version` et l'ouvre."""
        self.ensure_one()
        new = self.document_id.action_new_version(self.file, self.file_name)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'oski.dms.document',
            'res_id': new.id,
            'view_mode': 'form',
            'target': 'current',
        }
