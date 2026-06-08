from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    oski_login_logo = fields.Binary(
        string="Logo de la page de connexion",
        help="Logo affiché sur la page de connexion (remplace le logo société).",
    )
