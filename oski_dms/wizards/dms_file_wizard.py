from odoo import fields, models


class DmsFileWizard(models.TransientModel):
    _name = 'oski.dms.file.wizard'
    _description = "Classer une pièce jointe dans la GED"

    attachment_id = fields.Many2one(
        'ir.attachment', string="Pièce jointe", required=True)
    workspace_id = fields.Many2one(
        'oski.dms.workspace', string="Espace", required=True)
    tag_ids = fields.Many2many('oski.dms.tag', string="Étiquettes")

    def action_file(self):
        """Classe la pièce jointe existante dans la GED sans dupliquer l'octet.

        `attachment_id` est passé directement à `create()` : l'inverse
        `_inverse_file` de `oski.dms.document` ne s'exécute pas (pas de
        `file` fourni), donc aucun nouvel `ir.attachment` n'est créé.
        """
        self.ensure_one()
        att = self.attachment_id
        doc = self.env['oski.dms.document'].create({
            'name': att.name,
            'workspace_id': self.workspace_id.id,
            'attachment_id': att.id,
            'tag_ids': [(6, 0, self.tag_ids.ids)],
            'res_model': att.res_model or False,
            'res_id': att.res_id or False,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'oski.dms.document',
            'res_id': doc.id,
            'view_mode': 'form',
        }
