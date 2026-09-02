from odoo import fields, models


class OskiModuleCategory(models.Model):
    _name = "oski.module.category"
    _description = "Store module category"
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True, translate=True)
    sequence = fields.Integer(default=10)
    parent_id = fields.Many2one(
        "oski.module.category", string="Parent category", ondelete="cascade"
    )
    module_ids = fields.One2many("oski.module", "category_id", string="Modules")
