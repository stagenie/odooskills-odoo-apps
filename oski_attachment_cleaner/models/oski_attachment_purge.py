from odoo import fields, models


class OskiAttachmentPurge(models.Model):
    _name = "oski.attachment.purge"
    _description = "Purge de pièces jointes"
    _order = "purged_on desc, id desc"
    _rec_name = "purged_on"

    purged_on = fields.Datetime(
        string="Purgée le", required=True, default=fields.Datetime.now, index=True)
    user_id = fields.Many2one(
        "res.users", string="Par", required=True, default=lambda self: self.env.user)
    attachment_count = fields.Integer(string="Pièces supprimées")
    # Colonne numérique : un entier de 32 bits plafonne à 2 Go libérés.
    freed_bytes = fields.Float(string="Octets libérés", digits=(16, 0))
    criteria = fields.Char(string="Critères")
    detail = fields.Text(string="Pièces")
