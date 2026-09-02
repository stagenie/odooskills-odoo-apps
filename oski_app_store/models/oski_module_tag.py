from odoo import fields, models


class OskiModuleTag(models.Model):
    _name = "oski.module.tag"
    _description = "Store module tag"
    _order = "name"

    name = fields.Char(string="Name", required=True, translate=True)
    color = fields.Integer(string="Color", default=0)
    active = fields.Boolean(string="Active", default=True)
    module_ids = fields.Many2many(
        "oski.module",
        "oski_module_tag_rel",
        "tag_id",
        "module_id",
        string="Modules",
    )

    _name_uniq = models.Constraint(
        "UNIQUE(name)",
        "A tag with this name already exists.",
    )
