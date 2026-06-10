from odoo import fields, models


class OskiModuleVersion(models.Model):
    _name = "oski.module.version"
    _description = "Archive d'un module pour une version Odoo donnée"
    _order = "odoo_version_id desc, released_date desc"

    module_id = fields.Many2one(
        "oski.module", string="Module", required=True, ondelete="cascade"
    )
    odoo_version_id = fields.Many2one(
        "oski.odoo.version",
        string="Version Odoo",
        ondelete="restrict",
        # required géré par la vue + contrainte : pas de NOT NULL SQL pour que
        # la migration post-update puisse remplir les lignes existantes.
    )
    odoo_version = fields.Char(
        string="Version Odoo (code)",
        related="odoo_version_id.name",
        store=True,
    )
    module_version = fields.Char(
        string="Version du module", required=True, default="19.0.1.0.0"
    )
    attachment_id = fields.Many2one("ir.attachment", string="Archive .zip")
    changelog = fields.Text(string="Notes de version")
    released_date = fields.Date(string="Date de publication")

    _version_uniq = models.Constraint(
        "UNIQUE(module_id, odoo_version_id)",
        "Une seule archive par version Odoo pour un module donné.",
    )
