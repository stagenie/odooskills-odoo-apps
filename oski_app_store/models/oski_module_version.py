from odoo import fields, models


class OskiModuleVersion(models.Model):
    _name = "oski.module.version"
    _description = "Archive d'un module pour une version Odoo donnée"
    _order = "odoo_version desc, released_date desc"

    module_id = fields.Many2one(
        "oski.module", string="Module", required=True, ondelete="cascade"
    )
    odoo_version = fields.Selection(
        [
            ("15.0", "15.0"),
            ("16.0", "16.0"),
            ("17.0", "17.0"),
            ("18.0", "18.0"),
            ("19.0", "19.0"),
        ],
        string="Version Odoo",
        required=True,
        default="19.0",
    )
    module_version = fields.Char(
        string="Version du module", required=True, default="19.0.1.0.0"
    )
    attachment_id = fields.Many2one("ir.attachment", string="Archive .zip")
    changelog = fields.Text(string="Notes de version")
    released_date = fields.Date(string="Date de publication")

    _version_uniq = models.Constraint(
        "UNIQUE(module_id, odoo_version)",
        "Une seule archive par version Odoo pour un module donné.",
    )
