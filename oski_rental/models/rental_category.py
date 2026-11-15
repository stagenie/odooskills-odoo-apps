from odoo import fields, models


class RentalCategory(models.Model):
    _name = 'oski.rental.category'
    _description = 'Rental Resource Category'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    image_128 = fields.Image(string='Image', max_width=128, max_height=128)
    description = fields.Text(string='Description')
