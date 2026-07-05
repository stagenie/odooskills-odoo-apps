from odoo import fields, models


class DmsTag(models.Model):
    _name = 'oski.dms.tag'
    _description = "Étiquette GED"
    _order = 'name'

    name = fields.Char(required=True)
    color = fields.Integer(string="Couleur")
    parent_id = fields.Many2one('oski.dms.tag', string="Catégorie", ondelete='set null')

    _name_uniq = models.Constraint(
        'UNIQUE (name)',
        "Cette étiquette existe déjà.")
