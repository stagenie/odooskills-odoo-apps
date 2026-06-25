from odoo import fields, models


class HelpdeskStage(models.Model):
    _name = "helpdesk.stage"
    _description = "Étape d'assistance"
    _order = "sequence, id"

    name = fields.Char(string="Nom", required=True)
    sequence = fields.Integer(string="Séquence", default=10)
    fold = fields.Boolean(string="Repliée")
    is_close = fields.Boolean(
        string="Étape terminale",
        help="Les tickets dans cette étape sont considérés comme résolus.")
