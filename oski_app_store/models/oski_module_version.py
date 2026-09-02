from odoo import fields, models


class OskiModuleVersion(models.Model):
    _name = "oski.module.version"
    _description = "Module archive for a given Odoo version"
    # m2o dans _order : délègue à l'ordre du comodèle ("sequence desc"),
    # inversé si DESC — donc "asc" ici = plus récente d'abord.
    _order = "odoo_version_id asc, released_date desc"

    module_id = fields.Many2one(
        "oski.module", string="Module", required=True, ondelete="cascade"
    )
    odoo_version_id = fields.Many2one(
        "oski.odoo.version",
        string="Odoo version",
        ondelete="restrict",
        # required géré par la vue + contrainte : pas de NOT NULL SQL pour que
        # la migration post-update puisse remplir les lignes existantes.
    )
    odoo_version = fields.Char(
        string="Odoo version (code)",
        related="odoo_version_id.name",
        store=True,
    )
    module_version = fields.Char(
        string="Module version", required=True, default="19.0.1.0.0"
    )
    attachment_id = fields.Many2one("ir.attachment", string=".zip archive")
    changelog = fields.Text(string="Release notes")
    released_date = fields.Date(string="Release date")
    download_count = fields.Integer(
        string="Downloads",
        default=0,
        readonly=True,
        help="Number of times this archive was served.",
    )

    _version_uniq = models.Constraint(
        "UNIQUE(module_id, odoo_version_id)",
        "Only one archive per Odoo version for a given module.",
    )

    def _bump_download_count(self):
        """Incrément SQL atomique : plusieurs workers peuvent servir le même zip."""
        self.ensure_one()
        self.env.cr.execute(
            "UPDATE oski_module_version SET download_count = COALESCE(download_count, 0) + 1 WHERE id = %s",
            [self.id],
        )
        self.invalidate_recordset(["download_count"])
        self.module_id.invalidate_recordset(["download_count"])
