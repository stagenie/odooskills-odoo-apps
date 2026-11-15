from odoo import fields, models


class DmsTag(models.Model):
    _name = 'oski.dms.tag'
    _description = "DMS Tag"
    _order = 'name'

    name = fields.Char(string="Name", required=True)
    color = fields.Integer(string="Color")
    parent_id = fields.Many2one('oski.dms.tag', string="Category", ondelete='set null')

    _name_uniq = models.Constraint(
        'UNIQUE (name)',
        "This tag already exists.")
