from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    oski_login_logo = fields.Binary(
        string="Login Page Logo",
        help="Logo shown on the login page (replaces the company logo).",
    )
