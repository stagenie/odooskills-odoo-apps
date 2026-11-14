from odoo import fields, models


class OskiAttachmentPurge(models.Model):
    _name = "oski.attachment.purge"
    _description = "Attachment Purge"
    _order = "purged_on desc, id desc"
    _rec_name = "purged_on"

    purged_on = fields.Datetime(
        string="Purged On", required=True, default=fields.Datetime.now, index=True)
    user_id = fields.Many2one(
        "res.users", string="By", required=True, default=lambda self: self.env.user)
    attachment_count = fields.Integer(string="Deleted Attachments")
    # Colonne numérique : un entier de 32 bits plafonne à 2 Go libérés.
    freed_bytes = fields.Float(string="Freed Bytes", digits=(16, 0))
    criteria = fields.Char(string="Criteria")
    detail = fields.Text(string="Attachments")
