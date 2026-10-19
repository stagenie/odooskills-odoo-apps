from odoo import fields, models


class OskiAuditLog(models.Model):
    _name = "oski.audit.log"
    _description = "Journal des modifications"
    _order = "create_date desc, id desc"
    _rec_name = "res_name"

    model_name = fields.Char(string="Modèle", required=True, index=True, readonly=True)
    model_label = fields.Char(string="Intitulé du modèle", readonly=True)
    res_id = fields.Integer(string="Identifiant", required=True, index=True, readonly=True)
    res_name = fields.Char(string="Enregistrement", readonly=True)
    operation = fields.Selection(
        [("create", "Création"), ("write", "Modification"), ("unlink", "Suppression")],
        string="Opération", required=True, readonly=True,
    )
    changes = fields.Text(string="Détail", readonly=True)
    user_id = fields.Many2one(
        "res.users", string="Auteur", required=True, readonly=True,
        default=lambda self: self.env.user, ondelete="restrict",
    )
    create_date = fields.Datetime(string="Date", readonly=True)
