from odoo import api, fields, models


class OskiModule(models.Model):
    _name = "oski.module"
    _description = "Module du store OdooSkills"
    _inherit = ["website.published.mixin"]
    _order = "name"

    name = fields.Char(string="Nom affiché", required=True, translate=True)
    technical_name = fields.Char(string="Nom technique", required=True)
    summary = fields.Char(string="Résumé", translate=True)
    description_html = fields.Html(string="Description", translate=True, sanitize=False)
    category_id = fields.Many2one("oski.module.category", string="Catégorie")
    license = fields.Selection(
        [("lgpl-3", "LGPL-3"), ("opl-1", "OPL-1"), ("other", "Propriétaire")],
        string="Licence",
        default="lgpl-3",
        required=True,
    )
    is_free = fields.Boolean(string="Gratuit", default=True)
    author = fields.Char(string="Auteur", default="OdooSkills")
    maintainer = fields.Char(string="Mainteneur", default="ADICOPS")
    version_line_ids = fields.One2many(
        "oski.module.version", "module_id", string="Versions"
    )
    dependency_ids = fields.Many2many(
        "oski.module",
        "oski_module_dependency_rel",
        "module_id",
        "dependency_id",
        string="Dépendances",
    )
    image_1920 = fields.Image(string="Icône")
    product_tmpl_id = fields.Many2one(
        "product.template", string="Produit lié", ondelete="restrict", copy=False
    )

    _technical_name_uniq = models.Constraint(
        "UNIQUE(technical_name)",
        "Le nom technique du module doit être unique.",
    )

    def _compute_website_url(self):
        for record in self:
            if record.id:
                record.website_url = "/apps/%s" % self.env["ir.http"]._slug(record)
            else:
                record.website_url = "#"

    def latest_version(self, odoo_version="19.0"):
        """Retourne la dernière oski.module.version pour une version Odoo."""
        self.ensure_one()
        return self.version_line_ids.filtered(
            lambda v: v.odoo_version == odoo_version
        )[:1]

    def available_versions(self):
        """Set des versions Odoo pour lesquelles ce module a une archive."""
        self.ensure_one()
        return set(self.version_line_ids.mapped("odoo_version"))

    def supports(self, odoo_version):
        """True si le module a une archive pour cette version Odoo."""
        self.ensure_one()
        return odoo_version in self.available_versions()

    def download_target(self, selected):
        """Version à servir : exacte si supportée, sinon dernière dispo.

        Retourne un recordset oski.module.version (vide si aucune version).
        """
        self.ensure_one()
        exact = self.version_line_ids.filtered(
            lambda v: v.odoo_version == selected
        )
        if exact:
            return exact[:1]
        return self.version_line_ids.sorted(
            lambda v: v.odoo_version, reverse=True
        )[:1]
