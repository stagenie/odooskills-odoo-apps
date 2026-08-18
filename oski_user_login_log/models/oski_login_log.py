from odoo import fields, models


class OskiLoginLog(models.Model):
    _name = "oski.login.log"
    _description = "Journal des connexions"
    _order = "create_date desc, id desc"
    _rec_name = "login"

    login = fields.Char(string="Identifiant saisi", required=True, index=True, readonly=True)
    user_id = fields.Many2one(
        "res.users", string="Utilisateur", readonly=True, ondelete="set null",
        help="Vide quand l'identifiant saisi ne correspond à aucun compte.",
    )
    result = fields.Selection(
        [("success", "Réussite"), ("failure", "Échec")],
        string="Résultat", required=True, index=True, readonly=True,
    )
    ip_address = fields.Char(string="Adresse IP", readonly=True)
    create_date = fields.Datetime(string="Date", readonly=True)
