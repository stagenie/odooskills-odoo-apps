from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    oski_module_id = fields.One2many(
        "oski.module", "product_tmpl_id", string="Store module"
    )
