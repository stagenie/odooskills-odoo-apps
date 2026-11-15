from odoo import fields, models


class OskiAuditLog(models.Model):
    _name = "oski.audit.log"
    _description = "Change Log"
    _order = "create_date desc, id desc"
    _rec_name = "res_name"

    model_name = fields.Char(string="Model", required=True, index=True, readonly=True)
    model_label = fields.Char(string="Model Label", readonly=True)
    res_id = fields.Integer(string="Record ID", required=True, index=True, readonly=True)
    res_name = fields.Char(string="Record", readonly=True)
    operation = fields.Selection(
        [("create", "Creation"), ("write", "Update"), ("unlink", "Deletion")],
        string="Operation", required=True, readonly=True,
    )
    changes = fields.Text(string="Details", readonly=True)
    user_id = fields.Many2one(
        "res.users", string="Author", required=True, readonly=True,
        default=lambda self: self.env.user, ondelete="restrict",
    )
    create_date = fields.Datetime(string="Date", readonly=True)
