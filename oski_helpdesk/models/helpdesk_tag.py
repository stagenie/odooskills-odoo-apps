from odoo import fields, models


class HelpdeskTag(models.Model):
    _name = "helpdesk.tag"
    _description = "Étiquette d'assistance"
    _order = "name"

    name = fields.Char(string="Nom", required=True)
    color = fields.Integer(string="Couleur")

    _unique_name = models.Constraint("UNIQUE(name)", "Une étiquette de ce nom existe déjà.")
