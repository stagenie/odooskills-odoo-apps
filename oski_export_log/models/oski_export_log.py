from odoo import fields, models


class OskiExportLog(models.Model):
    _name = "oski.export.log"
    _description = "Export Log"
    _order = "create_date desc, id desc"
    _rec_name = "model_label"

    model_name = fields.Char(string="Model", required=True, index=True, readonly=True)
    model_label = fields.Char(string="Model Description", readonly=True)
    record_count = fields.Integer(string="Exported Rows", readonly=True)
    field_count = fields.Integer(string="Field Count", readonly=True)
    field_names = fields.Text(string="Exported Fields", readonly=True)
    user_id = fields.Many2one(
        "res.users", string="Exported By", required=True, readonly=True,
        default=lambda self: self.env.user, ondelete="restrict",
    )
    create_date = fields.Datetime(string="Date", readonly=True)
