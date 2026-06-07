from odoo import fields, models


class OskiModuleTag(models.Model):
    _name = "oski.module.tag"
    _description = "Tag de module du store"
    _order = "name"

    name = fields.Char(string="Nom", required=True, translate=True)
    color = fields.Integer(string="Couleur", default=0)
    active = fields.Boolean(string="Actif", default=True)
    module_ids = fields.Many2many(
        "oski.module",
        "oski_module_tag_rel",
        "tag_id",
        "module_id",
        string="Modules",
    )

    _name_uniq = models.Constraint(
        "UNIQUE(name)",
        "Un tag du même nom existe déjà.",
    )
