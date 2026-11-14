from odoo import fields, models


class HelpdeskTag(models.Model):
    _name = "helpdesk.tag"
    _description = "Helpdesk Tag"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    color = fields.Integer(string="Color")

    _unique_name = models.Constraint("UNIQUE(name)", "A tag with the same name already exists.")
