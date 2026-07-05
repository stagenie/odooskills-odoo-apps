from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def action_file_in_dms(self):
        """Ouvre le wizard de classement GED pré-rempli avec cet attachment."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': "Classer dans la GED",
            'res_model': 'oski.dms.file.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_attachment_id': self.id},
        }
