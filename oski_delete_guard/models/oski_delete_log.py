from odoo import fields, models


class OskiDeleteLog(models.Model):
    """Trace d'une suppression réellement exécutée sur un modèle surveillé."""

    _name = "oski.delete.log"
    _description = "Deletion Log"
    _order = "create_date desc, id desc"
    _rec_name = "res_name"

    model_name = fields.Char(string="Model", required=True, index=True, readonly=True)
    model_label = fields.Char(string="Model Description", readonly=True)
    res_id = fields.Integer(string="Deleted ID", required=True, readonly=True)
    res_name = fields.Char(string="Record", readonly=True)
    user_id = fields.Many2one(
        "res.users", string="Deleted By", required=True, readonly=True,
        default=lambda self: self.env.user, ondelete="restrict",
    )
    create_date = fields.Datetime(string="Date", readonly=True)
