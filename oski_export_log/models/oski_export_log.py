from odoo import fields, models


class OskiExportLog(models.Model):
    _name = "oski.export.log"
    _description = "Journal des exports"
    _order = "create_date desc, id desc"
    _rec_name = "model_label"

    model_name = fields.Char(string="Modèle", required=True, index=True, readonly=True)
    model_label = fields.Char(string="Intitulé du modèle", readonly=True)
    record_count = fields.Integer(string="Lignes exportées", readonly=True)
    field_count = fields.Integer(string="Champs demandés", readonly=True)
    field_names = fields.Text(string="Champs", readonly=True)
    user_id = fields.Many2one(
        "res.users", string="Auteur", required=True, readonly=True,
        default=lambda self: self.env.user, ondelete="restrict",
    )
    create_date = fields.Datetime(string="Date", readonly=True)
